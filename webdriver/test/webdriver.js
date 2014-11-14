var nightmare = require('nightmare');
var should = require('should');
var fs = require('fs');
var path = require('path');
var inputDir = "/titb/webdriver/input/";
var outputDir= "/titb/webdriver/output/";
it('test all', function(done1) {
  this.timeout(30000);
  var counter = 0;
  fs.readdir(inputDir, function(err, res) {
    var tests = res;
    for (var i = 0; i < tests.length; i++) {
      var runTest = function(fileName) {
      fs.readFile(
          path.join(inputDir, fileName),
          'utf8',
          function (err, input) {
            fs.readFile(
              // input name == a.c -> expected output file name == a.txt
              path.join(outputDir, path.basename(fileName, '.c') + ".txt"),
              'utf8',
              function (err, expected) {
                var n = new nightmare({timeout: 15000});
                n.goto("http://localhost")
                  // Type in the code we want to pass to KLEE
                  .evaluate(updateCode, function(res){}, input)
                  .click('input[type=submit]')
                  // Wait till result-panel comes up
                  .wait("#result-output")
                  // Retrieve the result and check if the expected result matches
                  .evaluate(getResult, function(actual) {
                      actual.should.match(expected)
                      counter++;
                      if (counter == tests.length) {
                        // notify that all the assertions happened
                        done1();
                      }
                  })
                  .run();
              }
            )
          }
        );
      };
      runTest(tests[i]);
    }
  })
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
