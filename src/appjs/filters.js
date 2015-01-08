var filters = angular.module('filters', [])

filters.filter('isNotEmpty', [
	function () {
	    var bar;
	    return function (obj) {
	        for (bar in obj) {
	            if (obj.hasOwnProperty(bar)) {
	                return true;
	            }
	        }
	        return false;
	    };
	}]);

filters.filter('truncate', [
	function () {
		return function(input, limit) {
			if(input.length <= limit) {
				return input;
			}
			return input.slice(0, limit) + "...";
		};
	}]);