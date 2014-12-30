var config = {
  lib: 'src/components',
  sass: 'src/sass',
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
        			}
        		]
        	}
        },
        uglify: {
        	dist: {
        		files: {
        			'<%= config.frontend_dist %>/js/lib.min.js': [
        				'<%= bower.directory %>/jquery/jquery.js',
        				'<%= bower.directory %>/underscore/underscore.js',
        			],
        			'<%= config.frontend_dist %>/js/lib.min.js': [
        				'<%= bower.directory %>/jquery/jquery.js',
        				'<%= bower.directory %>/underscore/underscore.js',
        			],
        			'<%= config.frontend_dist %>/js/vendor/bootstrap.min.js': [
        				'<%= bower.directory %>/bootstrap-sass-official/assets/javascripts/bootstrap.js',
        				'<%= bower.directory %>/bootstrap-sass-official/assets/javascripts/bootstrap/*.js',
        			],
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
                files: ['<%= config.sass %>/*.scss'],
                tasks: ['sass'],
                options: {
                    spawn: false
                }
            }
        }
    });

	grunt.loadNpmTasks("grunt-contrib-sass");
	grunt.loadNpmTasks("grunt-contrib-watch");
	grunt.loadNpmTasks('grunt-contrib-copy');
	grunt.loadNpmTasks('grunt-contrib-uglify');

	grunt.registerTask('default', [
		'copy',
		'uglify',
		'sass',
	]);

};
