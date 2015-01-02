var app = angular.module('app', [
    'ngResource',
    'ngCookies',
    'ngAnimate',
    'ui.codemirror',
    'pusher-angular'
]);

app.config([
    '$httpProvider', '$interpolateProvider', '$resourceProvider',
    function ($httpProvider, $interpolateProvider, $resourceProvider) {
        $interpolateProvider.startSymbol('[[');
        $interpolateProvider.endSymbol(']]');
        $resourceProvider.defaults.stripTrailingSlashes = false;
    }]);

app.run([
    '$http', '$cookies',
    function ($http, $cookies) {
        $http.defaults.headers.post['X-CSRFToken'] = $cookies.csrftoken;
        $http.defaults.headers.put['X-CSRFToken'] = $cookies.csrftoken;
        $http.defaults.headers.common['X-CSRFToken'] = $cookies.csrftoken;
    }]);


app.controller('MainCtrl', [
    '$scope', '$http', '$pusher',
    function ($scope, $http, $pusher) {
        $scope.submission = {
            code: '',
            args: {}
        };

        // Setup pusher 
        var pusher = $pusher(pclient);
        var channel_id = null;

        $scope.views = {
            main: true,
            results: false
        };

        $scope.switchTab = function (tab) {
            for (var view in $scope.views) {
                $scope.views[view] = false;
            }
            $scope.views[tab] = true;
        };

        $scope.examples = null;

        $scope.change = function () {
            $scope.submission = angular.copy($scope.examples[$scope.selected]);
            $scope.submission.args.stdin_enabled = !($scope.submission.args.numFiles == 0 && $scope.submission.args.sizeFiles == 0);
        };

        $http.get('/examples').
            success(function (data, status, headers, config) {
                $scope.examples = data;
                $scope.exampleKeys = Object.keys(data);


                // Hack, TODO: add boolean for default value.
                if ($scope.exampleKeys.length > 0) {
                    $scope.selected = "Hello World";
                    $scope.change();
                }
            }).error(function (data, status, headers, config) {
                console.log("Error loading tutorial examples.");
            });

        $scope.submission.args.stdin_enabled = false;
        $scope.stdinArgs = false;
        $scope.progress = [];
        $scope.result = {};

        $scope.editorOptions = {
            viewportMargin: 5,
            lineWrapping: true,
            lineNumbers: true,
            mode: 'clike'
        };

        $scope.resetStdin = function () {
            $scope.stdinArgs = false;
            $scope.submission.args.minStdinArgs = 0;
            $scope.submission.args.maxStdinArgs = 0;
            $scope.submission.args.sizeStdinArgs = 0;
        };
        
        $scope.processForm = function (submission) {
            if (channel_id) {
                pusher.unsubscribe(channel_id);
            }
            $scope.result = {};
            $scope.progress = [];
            $scope.progress.push('Job queued!');

            $http
                // Send data to submit endpoint
                .post('/submit/', submission)
                // We get a task id from submitting!
                .success(
                function (data, status, headers) {
                    channel_id = data.task_id;
                    var channel = pusher.subscribe(channel_id);

                    channel.bind('notification', function (response) {
                        data = angular.fromJson(response.data);

                        // No guarantee of order? latency issues?
                        if (data.result) {
                            $scope.result = data.result;
                        } else {
                            $scope.progress.push(data.message);
                        }
                    });

                    channel.bind('job_complete', function (response) {
                        data = angular.fromJson(response.data);
                        $scope.progress.push('Done!');
                        $scope.result = data.result;
                    });

                    channel.bind('job_failed', function (response) {
                        data = angular.fromJson(response.data);
                        $scope.result = {
                            'output': data.output
                        };
                    });

                }
            )
                // We didn't even get a task back from submit
                .error(
                function (data, status, headers) {
                    console.debug('Error! ', data);
                }
            );

        };
    }]
);

var isNotEmpty = function () {
    var bar;
    return function (obj) {
        for (bar in obj) {
            if (obj.hasOwnProperty(bar)) {
                return true;
            }
        }
        return false;
    }
};
app.filter('isNotEmpty', isNotEmpty);
