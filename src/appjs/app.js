var app = angular.module('app', [

    // Vendor
    'ngResource',
    'ngCookies',
    'ngAnimate',
    'ui.codemirror',
    'ui.bootstrap',
    'ui.bootstrap.dropdown',
    'ui.slider',
    'pusher-angular',

    // App
    'services',
    'controllers',
    'filters',
    'directives',
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
