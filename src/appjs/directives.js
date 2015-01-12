var directives = angular.module('directives', []);

directives.directive('ngEnter', [
    function() {
        return function (scope, element, attrs) {
            element.bind("keydown keypress", function (event) {
                if (event.which === 13) {
                    scope.$apply(function () {
                        scope.$eval(attrs.ngEnter);
                    });
                    event.preventDefault();
                }
            });
        };
    }
]);

directives.directive('focus', [
    '$timeout',
    function ($timeout) {
        return {
            scope: {
                focus: '@'
            },
            link: function (scope, element) {
                function doFocus() {
                    $timeout(function () {
                        element[0].focus();
                    });
                };

                if (scope.focus != null) {
                    // focus unless attribute evaluates to 'false'
                    if (scope.focus !== 'false') {
                        doFocus();
                    }

                    // focus if attribute value changes to 'true'
                    scope.$watch('focus', function(value) {
                        if (value === 'true') {
                            doFocus();
                        }
                    });
                } else {
                    // if attribute value is not provided - always focus
                    doFocus();
                }
            }
        };
    }
]);

// Monkey patch
directives.directive('cmlCodemirrorRefresh', [
    '$timeout',
    function ($timeout) {
        return {
            restrict: 'C',
            link: function (scope, element, attrs) {
                attrs.$observe('uiRefresh', function(value) {
                    scope.$watch(value, function (newValue) {
                        $timeout(function () {
                            element.children()[0].CodeMirror.refresh();
                        }, 100);
                    });
                });
            }
        };
    }
]);


directives.directive('neatFileUploader', [
    function () {
        return {
            restrict: 'E',
            replace: true,
            scope: {
                uploader: '='
            },
            link: function (scope, element, attrs) {
                element.find('a').click(function (e) {
                    element.find('input[type="file"]').click();
                });
            },
            template: '<div class="file-uploader">'
                    +   '<a href="#">'
                    +       'Upload File'
                    +       '<i class="icon_cloud-upload_alt"></i>'
                    +   '</a>'
                    +   '<input type="file" nv-file-select uploader="uploader" style="display: none;" />'
                    + '</div>'
        };
    }
]);
