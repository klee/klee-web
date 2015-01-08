var services = angular.module('services', ['ngResource']);

services.factory('Project', [
    '$resource', 
    function ($resource) {
        return $resource('/api/projects/:id', {id: '@id'},
            {
                'update': { 
                    method:'PUT' 
                }
            });
    }]);

services.factory('File', [
    '$resource', 
    function ($resource) {
        return $resource('/api/projects/:projectId/files/:fileId', 
            { 
                projectId: '@projectId',
                fileId: '@id' 
            },
            {
                'update': { 
                    method:'PUT' 
                }
            });
    }]);