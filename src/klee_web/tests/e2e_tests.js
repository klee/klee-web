var Promise = require("bluebird");
var nightmare = require('nightmare');
var should = require('should');
var fs = Promise.promisifyAll(require('fs'));
var path = require('path');

var inputDir = path.join(__dirname, "input");
var outputDir= path.join(__dirname, "output");

it('test all', function(done1) {
  this.timeout(20000);
  var testsRun = 0;

  var runAllTests = function(tests) {
    for (var i = 0; i < tests.length; i++) {
      var fileName = tests[i];
      var inputFuture = fs.readFileAsync(path.join(inputDir, fileName), 'UTF8');

      var expectedOutputFile = path.join(outputDir,
        path.basename(fileName, ".c") + ".txt");
      var expectedOutputFuture = fs.readFileAsync(expectedOutputFile, 'UTF8');

      Promise.join(inputFuture, expectedOutputFuture, function(input, expected) {
          var n = new nightmare({load: 1000, webSecurity: false});
          n.goto("http://localhost")
            // Type in the code we want to pass to KLEE
            .evaluate(updateCode, function(res){}, input)
            .click("#run-klee-btn")
            .wait("#result-output")
            .wait("code")
            // Retrieve the result and check if the expected result matches
            .evaluate(getResult, function(actual) {
                actual.replace(/(?:\r\n|\r|\n)/g, "\n").should.match(expected)
                testsRun++;
                if (testsRun == tests.length) {
                  // notify that all the assertions happened
                  done1();
                }
            }).run();
      })
    }
    var n = new nightmare({ webSecurity: false });

    // Check that admin can login
    n.goto("http://localhost/admin")
    .wait('login')
    .type("#id_username", 'admin')
    .type("#id_password", 'development')

    .click('[type=submit]')
    .wait('dashboard')

    .evaluate(getTitle, function(res) {
      res.should.match("Site administration | Django site admin")
      done1();
    })
    .run();
  }

  fs.readdirAsync(inputDir).then(runAllTests);
});

function updateCode(newCode) {
  var codeMirrorElement = $("#codemirror").get(0);
  var scope = angular.element(codeMirrorElement).scope();
  scope.submission.code = newCode;
  scope.$apply();
  return true;
}

function getResult() {
  return document.querySelector('#result-output').innerText;
}
