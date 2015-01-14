var controllers = angular.module('controllers', []);

controllers.controller('MainCtrl', [
    '$scope', '$http', '$pusher', '$rootScope', 'Project', 'File',
    function($scope, $http, $pusher, $rootScope, Project, File) {
        // Setup pusher 
        var pusher = $pusher(pclient);
        var channelId = null;

        $scope.submission = {
            name: null,
            code: '',
            runConfiguration: {
                symArgs: {
                    range: [0, 0],
                    size: 0
                },
                stdinEnabled: false,
                numFiles: 0,
                sizeFiles: 0
            }
        };
        $scope.defaultSubmission = angular.copy($scope.submission);

        $scope.opts = {
            symArgs: {
                enabled: false,
                open: false
            },
            symFiles: {
                enabled: false,
                open: false
            }
        };

        $scope.progress = [];
        $scope.result = {};
        $scope.submitted = false;

        $scope.editor = null;
        $scope.selectedProject = null;

        $scope.projects = [];
        $scope.files = [];

        $scope.toggleSymArgs = function ($event) {
            $event.preventDefault();
            $event.stopPropagation();
            $scope.opts.symArgs.enabled = !$scope.opts.symArgs.enabled;
            $scope.opts.symArgs.open = !$scope.opts.symArgs.open;
        };

        $scope.toggleSymFiles = function ($event) {
            $event.preventDefault();
            $event.stopPropagation();
            $scope.opts.symFiles.enabled = !$scope.opts.symFiles.enabled;
            $scope.submission.runConfiguration.stdinEnabled = !$scope.submission.runConfiguration.stdinEnabled;
            $scope.opts.symFiles.open = !$scope.opts.symFiles.open;
        };

        $scope.resetSymArgs = function() {
            $scope.opts.symArgs.enabled = false;
            $scope.submission.runConfiguration.symArgs = {
                range: [0, 0],
                size: 0
            };
        };

        $scope.resetSymFiles = function() {
            $scope.opts.symFiles.enabled = false;
            $scope.submission.runConfiguration.stdinEnabled = false; 
        };

        $scope.resetLoadedFile = function() {
            $scope.submission = angular.copy($scope.defaultSubmission);
        }

        var saveTimeout = null;
        var lastSaveTime = 0;
        const MIN_SAVE_INTERVAL = 2000; // 2 seconds

        var saveSubmission = function() {
            var submission = $scope.submission;
            if (!angular.isUndefined($scope.submission.$update) && !$scope.selectedProject.example) {
                File.update({}, submission);
            }

            lastSaveTime = Date.now();
            saveTimeout = null;
        };

        $scope.$watch('submission', function(newVal, oldVal) {
            if (newVal !== oldVal && saveTimeout == null) {
                var nextSave = ((lastSaveTime + MIN_SAVE_INTERVAL) - Date.now());
                var timeToSave = Math.max(nextSave, 0);
                saveTimeout = setTimeout(saveSubmission, timeToSave);
            }
        }, true);

        $scope.processForm = function(submission) {
            $rootScope.startNanobar();
            $scope.submitted = true;
            $scope.result = {};
            $scope.progress = [];
            $scope.progress.push('Job queued!');

            if (channelId) {
                pusher.unsubscribe(channelId);
            }

            // Send data to submit endpoint
            $http
                .post('/api/jobs/submit/', submission)

            // We get a task id from submitting!
            .success(
                function(data, status, headers) {
                    channelId = data.taskId;
                    var channel = pusher.subscribe(channelId);

                    channel.bind('notification', function(response) {
                        data = angular.fromJson(response.data);
                        $scope.progress.push(data.message);
                    });

                    channel.bind('job_complete', function(response) {
                        $scope.submitted = false;
                        data = angular.fromJson(response.data);
                        $scope.progress.push('Done!');
                        $scope.result = data;
                        $rootScope.finishNanobar();
                    });

                    channel.bind('job_failed', function(response) {
                        $scope.submitted = false;
                        data = angular.fromJson(response.data);
                        $scope.result = data;
                        $rootScope.finishNanobar();
                    });

                }
            )

            // We didn't even get a task back from submit
            .error(
                function(data, status, headers) {
                    console.debug('Error! ', data);
                    $rootScope.finishNanobar();
                }
            );
        };

        $scope.codemirrorLoaded = function(_editor) {
            $scope.editor = _editor;

            _editor.setOption('viewportMargin', 5);
            _editor.setOption('lineWrapping', true);
            _editor.setOption('lineNumbers', true);
            _editor.setOption('mode', {
                name: 'text/x-csrc',
                useCPP: true
            });
            _editor.setOption('readOnly', 'nocursor');
            _editor.setOption('theme', 'neo');
        };

        $scope.drawCoverage = function(coverage) {
            $scope.editor.setValue($scope.submission.code);

            var linesHit = 0;
            var linesTotal = 0;
            var lines = coverage.lines;
            for (var i = 0; i < lines.length; i++) {
                var hit = lines[i].hit;
                if (hit == null) {
                    $scope.editor.addLineClass(i, 'wrap', 'line-null');
                } else {
                    if (hit > 0) {
                        linesHit += 1;
                        $scope.editor.addLineClass(i, 'wrap', 'line-hit');
                    } else {
                        $scope.editor.addLineClass(i, 'wrap', 'line-miss');
                    }
                    linesTotal += 1;
                }
            }
            $scope.editor.addLineClass(lines.length, 'wrap', 'line-null');

            $scope.linePercentage = (linesHit / linesTotal).toFixed(2) * 100;

            $scope.editor.focus();
        };

        $scope.$watch('result', function (result) {
            if (!(angular.isUndefined(result.coverage) || result.coverage === null)) {
                $scope.drawCoverage(result.coverage[0]);
            }
        });
    }
]);


controllers.controller('EditorCtrl', [
    '$scope',
    function($scope) {
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
    }
]);


controllers.controller('SidebarCtrl', [
    '$scope', 'Project', 'File', 'FileUploader', '$cookies',
    function($scope, Project, File, FileUploader, $cookies) {

        function refreshFiles (projectId, selectedFileId) {
            var refreshFiles = File.query({
                projectId: projectId
            }).$promise;

            refreshFiles.then(function (files) {
                $scope.files = files;
                var selectedFile = _.findWhere($scope.files, {
                    id: selectedFileId
                });
                $scope.selectFile(selectedFile);
            });
        };

        $scope.projectToAdd = false;
        $scope.newFile = {
            name: '',
            showForm: false
        };
        $scope.newProjectOpt = {
            name: 'Add New Project'
        };

        $scope.uploader = new FileUploader({
            withCredentials: true,
            autoUpload: true,
            removeAfterUpload: true,
            headers: {
                'X-CSRFToken': $cookies.csrftoken
            },
            onSuccessItem: function (item, response, status, headers) {
                refreshFiles($scope.selectedProject.id, response.id);
            },
            onErrorItem: function (item, response, status, headers) {
                alert('Upload failed. Please make sure you\'re uploading a valid file and try again.');
            },
        });

        Project.query().$promise.then(function(projects) {
            $scope.projects = projects;

            if (projects.length > 0) {
                $scope.$parent.selectedProject = projects[0];
            }

            // Only show new project option if project list is empty
            // or user is logged in (no example projects)
            if (projects.length == 0 || !$scope.$parent.selectedProject.example) {
                $scope.projects.push($scope.newProjectOpt);
            }
        });

        $scope.$watch('selectedProject', function(project) {
            if (!(_.isNull(project) || _.isUndefined(project))) {
                if (project.name == 'Add New Project') {
                    $scope.projectToAdd = true;
                } else {
                    // Update file uploader
                    $scope.uploader.url = 'api/projects/' + project.id + '/files/upload/';

                    refreshFiles(project.id, project.defaultFile);
                }
            } else {
                $scope.files = [];
                $scope.resetLoadedFile();
            }
        });

        $scope.selectFile = function (file) {
            if (!angular.isUndefined(file)) {
                var selectedProject = $scope.$parent.selectedProject;
                $scope.$parent.submission = file;
                selectedProject.defaultFile = file.id;
                
                if (!selectedProject.example) {
                    selectedProject.$update();
                }
            } else {
                $scope.resetLoadedFile();
            }
        };

        $scope.resetProjectSelector = function() {
            $scope.projectToAdd = false;
            $scope.$parent.selectedProject = null;
        };

        $scope.addProject = function (projectName) {
            var newProject = new Project({
                name: projectName
            });
            newProject.$save(function(project) {
                $scope.projects.push(project);
                $scope.$parent.selectedProject = project;
                $scope.projectToAdd = false;
            });
        };

        $scope.showAddFile = function() {
            $scope.newFile.showForm = true;
        };

        $scope.addFile = function() {
            var filename = $scope.newFile.name;
            // Hacky force append '.c'
            var re = /\.c$/;
            if (!re.test(filename)) {
                filename = filename + '.c';
            }

            var blankFile = new File({
                projectId: $scope.$parent.selectedProject.id,
                name: filename,
                code: '// Edit ' + filename,
                runConfiguration: {
                    symArgs: {
                        range: [0, 0],
                        size: 0
                    },
                    stdinEnabled: false,
                    numFiles: 0,
                    sizeFiles: 0
                }
            });

            blankFile.$save(function(newFile) {
                $scope.files.unshift(newFile);
                $scope.newFile.name = '';
                $scope.newFile.showForm = false;

                $scope.selectFile(blankFile);
            });
        };

        $scope.deleteFile = function(file) {
            file.$delete(function () {
                // If we're deleting the current file, reset the editor
                if (file == $scope.submission) {
                    $scope.resetLoadedFile();
                }

                // Remove from file list
                $scope.files = _.without($scope.files, file);
            });
        };

    }
]);


controllers.controller('ResultTabsCtrl', [
    '$scope',
    function($scope) {
        $scope.tabs = {
            output: {
                active: true
            },
            coverage: {
                active: false
            }
        };

        $scope.hideAllTabs = function() {
            angular.forEach($scope.tabs, function(tab, name) {
                $scope.tabs[name].active = false;
            });
        };

        $scope.setTab = function(tab) {
            if (tab in $scope.tabs) {
                $scope.hideAllTabs();
                $scope.tabs[tab].active = true;
            }
        };

        // Switch tab back to output if we hit submit
        $scope.$watch('submitted', function(submitted) {
            if (submitted) {
                $scope.setTab('output');
            }
        });

    }
]);
