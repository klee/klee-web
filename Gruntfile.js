var config = {
  lib: 'src/components',
  sass: 'src/sass',
  app: 'src/appjs',
  frontend_dist: 'src/klee_web/frontend/static/frontend/dist'
};

module.exports = function (grunt) {

    // Project configuration.
    grunt.initConfig({
        config: config,
        pkg: grunt.file.readJSON('package.json'),
        bower: grunt.file.readJSON('./.bowerrc'),
        copy: {
        	dist: {
        		files: [
        			// Copy Bootstrap sass to sass working dir
        			{
        				expand: true,
        				cwd: '<%= config.lib %>/bootstrap-sass-official/assets/stylesheets/bootstrap',
        				src: ['**/*'],
        				dest: '<%= config.sass %>/bootstrap'
        			},
        			// Copy Bootstrap assets to dist dirs
        			{
        				expand: true,
                        cwd: '<%= config.lib %>/bootstrap-sass-official/assets/fonts',
                        src: ['**/*'],
                        dest: '<%= config.frontend_dist %>/fonts'
                    },
                    // Elegant Icons
                    {
                        expand: true,
        				cwd: '<%= config.lib %>/elegant-icons/fonts',
                        src: ['*'],
                        dest: '<%= config.frontend_dist %>/css/vendor/fonts'
                    },
                    // Animate.css
                    {
                        expand: true,
                        cwd: '<%= config.lib %>/animate.css',
                        src: ['animate.min.css'],
                        dest: '<%= config.frontend_dist %>/css/vendor'
                    },
                    {
                        expand: true,
                        cwd: '<%= config.lib %>/elegant-icons/css',
                        src: ['style.css'],
                        dest: '<%= config.frontend_dist %>/css/vendor/eleganticons'
                    },
                    // Codemirror
                    {
                        expand: true,
                        cwd: '<%= config.lib %>/codemirror/lib',
        				src: 'codemirror.css',
        				dest: '<%= config.frontend_dist %>/css/vendor/codemirror'
        			},
                    {
                        expand: true,
                        cwd: '<%= config.lib %>/codemirror/theme',
                        src: ['*.css'],
                        dest: '<%= config.frontend_dist %>/css/vendor/codemirror/theme'
                    },
                    // Angular Codemirror
                    {
                        expand: true,
                        cwd: '<%= config.lib %>/angular-ui-codemirror',
                        src: 'ui-codemirror.min.js',
                        dest: '<%= config.frontend_dist %>/js/vendor'
                    },
                    // JQuery UI slider
                    {
                        expand: true,
                        cwd: '<%= config.lib %>/jquery-ui/themes/base/minified',
                        src: 'jquery-ui.min.css',
                        dest: '<%= config.frontend_dist %>/css/vendor'
                    },
                    {
                        expand: true,
                        cwd: '<%= config.lib %>/jquery-ui/ui/minified',
                        src: 'jquery-ui.min.js',
                        dest: '<%= config.frontend_dist %>/js/vendor'
                    },
        		]
        	}
        },
        concat: {
            dist: {
                files: [
                    {
                        '<%= config.frontend_dist %>/js/vendor/lib.min.js': [
                            '<%= bower.directory %>/jquery/dist/jquery.min.js',
                            '<%= bower.directory %>/underscore/underscore-min.js',
                        ],
                        '<%= config.frontend_dist %>/js/vendor/angular-custom.min.js': 
                            [
                                '<%= bower.directory %>/angular/angular.min.js',
                                '<%= bower.directory %>/angular-resource/angular-resource.min.js',
                                '<%= bower.directory %>/angular-cookies/angular-cookies.min.js',
                                '<%= bower.directory %>/angular-animate/angular-animate.min.js',
                            ],
                        '<%= config.frontend_dist %>/js/vendor/pusher-with-angular.min.js':
                            [
                                '<%= bower.directory %>/pusher/dist/pusher.min.js',
                                '<%= bower.directory %>/pusher-angular/lib/pusher-angular.min.js',
                            ],
                        '<%= config.frontend_dist %>/js/vendor/angular-bootstrap.min.js':
                            [
                                '<%= bower.directory %>/angular-bootstrap/ui-bootstrap.min.js',
                                '<%= bower.directory %>/angular-bootstrap/ui-bootstrap-tpls.min.js',
                            ],
                    }
                ]
            }
        },
        uglify: {
        	dist: {
        		files: {
                    '<%= config.frontend_dist %>/js/vendor/bootstrap.min.js': [
                        '<%= bower.directory %>/bootstrap-sass-official/assets/javascripts/bootstrap.js',
                        '<%= bower.directory %>/bootstrap-sass-official/assets/javascripts/bootstrap/*.js',
                    ],
                    '<%= config.frontend_dist %>/js/vendor/codemirror.min.js': [
                        '<%= bower.directory %>/codemirror/lib/codemirror.js',
                        // C syntax
                        '<%= bower.directory %>/codemirror/mode/clike/clike.js',
                    ],
                    '<%= config.frontend_dist %>/js/vendor/angular-ui-slider.min.js': [
                        '<%= bower.directory %>/angular-ui-slider/src/slider.js',
                    ],

                    // Application JS
        			'<%= config.frontend_dist %>/js/app.min.js': [
                        '<%= config.app %>/app.js'
                    ]
        		}
        	}
        },
        sass: {
        	dist: {
        		options: {
        			style: 'compressed'
        		},
                files: [
                    {
                        expand: true,
                        cwd: '<%= config.sass %>',
                        src: ['*.scss'],
                        dest: '<%= config.frontend_dist %>/css',
                        ext: '.css'
                    }
                ]
            }
        },
        watch: {
            sass: {
                files: [
                    '<%= config.sass %>/*.scss',
                    '<%= config.sass %>/components/*.scss',
                ],
                tasks: ['sass'],
                options: {
                    spawn: false
                }
            },
            app: {
                files: [
                    '<%= config.app %>/*.js'
                ],
                tasks: ['uglify'],
                options: {
                    spawn: false
                }
            }
        }
    });

	grunt.loadNpmTasks("grunt-contrib-sass");
	grunt.loadNpmTasks("grunt-contrib-watch");
    grunt.loadNpmTasks('grunt-contrib-copy');
	grunt.loadNpmTasks('grunt-contrib-concat');
	grunt.loadNpmTasks('grunt-contrib-uglify');

	grunt.registerTask('default', [
        'concat',
        'copy',
		'uglify',
		'sass',
	]);

};
