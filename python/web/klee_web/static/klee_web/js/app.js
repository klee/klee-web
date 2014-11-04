var app = angular.module('app', [
    'ngResource',
    'ngCookies',
    'ngAnimate',
    'ui.codemirror',
    'pusher-angular'
]);

app.config(function ($httpProvider, $interpolateProvider, $resourceProvider) {

    $interpolateProvider.startSymbol('[[');
    $interpolateProvider.endSymbol(']]');

    $resourceProvider.defaults.stripTrailingSlashes = false;
}).run(function ($http, $cookies) {
    $http.defaults.headers.post['X-CSRFToken'] = $cookies.csrftoken;
    $http.defaults.headers.put['X-CSRFToken'] = $cookies.csrftoken;
    $http.defaults.headers.common['X-CSRFToken'] = $cookies.csrftoken;
});


app.controller('MainCtrl',
    function ($scope, $http, $pusher) {
        // Setup pusher 
        var pusher = $pusher(pclient);

        $scope.submission = {
            code: '#include <stdio.h>\nint main()\n{\n\tprintf("Hello world\\n");\n\treturn 0;\n}'
        };
        $scope.progress = [];
        $scope.result = {};

        $scope.editorOptions = {
            viewportMargin: 5,
            lineWrapping : true,
            lineNumbers: true,
            mode: 'clike'
        };

        $scope.processForm = function (submission) {
            $scope.progress.push('Start!');
            $http
                // Send data to submit endpoint
                .post('/submit/', submission)
                // We get a task id from submitting!
                .success( 
                    function (data, status, headers) {
                        var channel_id = data.task_id;
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
                    }
                )
                // We didn't even get a task back from submit
                .error(
                    function (data, status, headers) {
                        console.debug('Error! ', data);
                    }
                );

        };
    }
);


app.filter('isNotEmpty', function () {
    var bar;
    return function (obj) {
        for (bar in obj) {
            if (obj.hasOwnProperty(bar)) {
                return true;
            }
        }
        return false;
    };
});