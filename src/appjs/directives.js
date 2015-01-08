var directives = angular.module('directives', []);

directives.directive('ngEnter', [
	function () {
	    return function (scope, element, attrs) {
	        element.bind("keydown keypress", function (event) {
	            if(event.which === 13) {
	                scope.$apply(function (){
	                    scope.$eval(attrs.ngEnter);
	                });
	                event.preventDefault();
	            }
	        });
	    };
	}]);

directives.directive('focus', [
	'$timeout',
	function ($timeout) {
		return {
		    scope: {
		      focus: '@'
		    },
		    link: function (scope, element) {
			    function doFocus() {
			        $timeout(function() {
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
    }]);

