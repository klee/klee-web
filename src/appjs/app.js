var app = angular.module('app', [
    'ngResource',
    'ngCookies',
    'ngAnimate',
    'ui.codemirror',
    'ui.bootstrap.dropdown',
    'ui.slider',
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
        // Setup pusher 
        var pusher = $pusher(pclient);
        var channel_id = null;

        $scope.submission = {
            code: '',
            args: {
                stdinArgs: {
                    range: [0, 0],
                    size: 0
                },
                stdin_enabled: false
            }
        };
        
        $scope.stdinArgs = false;
        $scope.progress = [];
        $scope.result = {};
        $scope.submitted = false;
        $scope.examples = null;

        $scope.changeExample = function () {
            $scope.submission = angular.copy($scope.examples[$scope.selectedExample]);
            $scope.stdinArgs = $scope.submission.args.range != [0, 0];
            $scope.submission.args.stdin_enabled = !($scope.submission.args.numFiles == 0 && $scope.submission.args.sizeFiles == 0);
        };

        // Load example projects
        $http.get('/examples').
            success(function (data, status, headers, config) {
                $scope.examples = data;
                $scope.exampleKeys = Object.keys(data);

                // Hack, TODO: add boolean for default value.
                if ($scope.exampleKeys.length > 0) {
                    $scope.selectedExample = "Files";
                    $scope.changeExample();
                }
            }).error(function (data, status, headers, config) {
                console.log("Error loading tutorial examples.");
            });


        $scope.editorOptions = {
            viewportMargin: 5,
            lineWrapping: true,
            lineNumbers: true,
            mode: {
                name: 'text/x-csrc',
                useCPP: true
            },
            theme: 'neo'
        };

        $scope.resetSymArgs = function () {
            $scope.stdinArgs = false;
            $scope.submission.args.stdinArgs = {
                range: [0, 0],
                size: 0
            };
        };
        
        $scope.processForm = function (submission) {
            $scope.submitted = true;            
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
                            $scope.progress.push(data.message);
                        });

                        channel.bind('job_complete', function (response) {
                            data = angular.fromJson(response.data);
                            $scope.progress.push('Done!');
                            $scope.result = data.result;
                            $scope.submitted = false;
                        });

                        channel.bind('job_failed', function (response) {
                            data = angular.fromJson(response.data);
                            $scope.result = {
                                'output': data.output
                            };
                            $scope.submitted = false;
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

app.controller('ResultTabsCtrl', [
    '$scope',
    function ($scope) {
        $scope.tabs = {
            output: {
                active: true 
            },
            coverage: {
                active: false
            }
        };

        $scope.hideAllTabs = function () {
            angular.forEach($scope.tabs, function (tab, name) {
                $scope.tabs[name].active = false;
            });
        };

        $scope.setTab = function (tab) {
            if (tab in $scope.tabs) {
                $scope.hideAllTabs();
                $scope.tabs[tab].active = true;
            }
        };

        // Switch tab back to output if we hit submit
        $scope.$watch('submitted', function (submitted) {
            if (submitted) {
                $scope.setTab('output');     
            }
        });

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
