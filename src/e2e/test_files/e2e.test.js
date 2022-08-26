const puppeteer = require("puppeteer");

jest.setTimeout(40000);
var WEBPAGE = process.env.WEBPAGE;
var ADMIN_PASSWORD = process.env.ADMIN_PASSWORD;
if (ADMIN_PASSWORD == null) {
  ADMIN_PASSWORD = "development";
}

describe("Input", () => {
  it("tests that basic klee-web job submission works", async () => {
    await page.goto("http://" + WEBPAGE + "/user/logout");
    await page.waitForSelector("#run-klee-btn")
    await page.waitForSelector('[ng-repeat="file in files"]');
    await page.click('[ng-repeat="file in files"]'); // select first file ... use page.select instead?
    await page.click("#run-klee-btn");
    await page.waitForSelector("#result-output");

    const text = await page.evaluate(
      () => document.querySelector("#result-output").innerText
    );
    await expect(text).toMatch(
      'KLEE: output directory is "/tmp/code/klee-out-0"\n' +
        "KLEE: Using STP solver backend\n\n" +
        "KLEE: done: total instructions = 33\n" +
        "KLEE: done: completed paths = 3\n" +
        "KLEE: done: partially completed paths = 0\n" +
        "KLEE: done: generated tests = 3"
    );
  });
});

describe("Admin", () => {
  it("tests that the admin can login", async () => {
    await page.goto("http://" + WEBPAGE + "/user/logout");
    await page.waitForSelector("#run-klee-btn")
    await page.goto("http://" + WEBPAGE + "/admin");
    await page.waitForSelector("#id_username");
    await page.waitForSelector("#id_password");

    await page.type("#id_username", "admin");
    await page.type("#id_password", ADMIN_PASSWORD);
    await Promise.all([
      page.click("[type=submit]"),
      page.waitForNavigation({ waitUntil: "networkidle0" })
    ]);
    var title = await page.title();
    await expect(title).toMatch("Site administration | Django site admin");
  });
});

describe("New Projects", () => {
  it("tests that logged users can add new projects", async () => {
    await page.goto("http://" + WEBPAGE + "/user/logout");
    await page.waitForSelector("#run-klee-btn")
    await page.goto("http://" + WEBPAGE + "/user/login");
    await page.waitForSelector("#id_username");
    await page.waitForSelector("#id_password");

    await page.type("[type=text]", "admin");
    await page.type("[type=password]", ADMIN_PASSWORD);
    await Promise.all([
      page.click("[type=submit]"),
      page.waitForNavigation({ waitUntil: "networkidle0" })
    ]);
    var content = await page.content();
    await expect(content).toMatch("Add New Project");
  });
});

describe("Klee Testcases", () => {
  it("tests that testcases window appears and is index-able", async () => {
    await page.goto("http://" + WEBPAGE + "/user/logout");
    await page.waitForSelector("#run-klee-btn");
    await page.waitForSelector('[ng-repeat="file in files"]');
    await page.click('[ng-repeat="file in files"]'); // select first file ... use page.select instead?
    await page.click("#run-klee-btn");
    await page.waitForSelector("#result-output"); // need to wait for KLEE to finish output
    await page.waitForSelector("#klee-testcases-btn");
    await page.click('#klee-testcases-btn');
    await page.waitForSelector("#klee-testcases-pagination");

    // Tests that there are 3 testcases
    const numTestcases =
        (await page.$$("#klee-testcases-pagination li")).length;
    const navButtons = 4;
    await expect(numTestcases).toBe(navButtons + 3);

    // Tests that there are 1 mem objs
    const numMemObjs =
        (await page.$$(".klee-testcases tbody tr")).length;
    await expect(numMemObjs).toBe(1);
    });
});

describe("Stats", () => {
  it("tests that stats window works", async () => {
    await page.goto("http://" + WEBPAGE + "/user/logout");
    await page.waitForSelector("#run-klee-btn");
    await page.waitForSelector('[ng-repeat="file in files"]');
    await page.click('[ng-repeat="file in files"]'); // select first file ... use page.select instead?
    await page.click("#run-klee-btn");
    await page.waitForSelector("#result-output");

    const text = await page.evaluate(
      () => document.querySelector("#result-output").innerText
    );
    const stdoutInstr = Number(
        text.match(/(?<=total instructions = )\d+/g)[0]
    );

    await page.waitForSelector("#stats-btn");
    await page.click("#stats-btn");

    // Tests that number of stats rows is 6
    const statRows = await page.$$(".klee-output tbody tr");
    await expect(statRows.length).toBe(6);

    // Tests number of instrs matches is 33
    const instrStat = await statRows[0].$$eval("td", tds => tds.map(
        td => td.textContent
    ));
    await expect(Number(instrStat[1])).toBe(stdoutInstr);
  });
});

describe("Coverage", () => {
  it("tests that coverage window works", async () => {
    await page.goto("http://" + WEBPAGE + "/user/logout");
    await page.waitForSelector("#run-klee-btn");
    await page.waitForSelector('[ng-repeat="file in files"]');
    await page.click('[ng-repeat="file in files"]'); // select first file ... use page.select instead?
    await page.waitForSelector(".coverage-btn");
    await page.click(".coverage-btn");
    await page.click("#run-klee-btn");
    await page.waitForSelector("#res-cov-btn");
    await page.click("#res-cov-btn");

    // Tests coverage text matches
    const covText = await page.$eval(
        ".klee-coverage pre",
        pre => pre.textContent
    );
    await expect(covText).toBe(" 100% of lines covered.");

    // Tests that top comment is not colored
    const commentText = await page.$eval(
        ".line-null .cm-comment",
        span => span.textContent
    );
    await expect(commentText).toBe("/*");

    // Tests that first hit should be get_sign function
    const firstHitText = await page.$eval(
        ".line-hit .cm-variable",
        span => span.textContent
    );
    await expect(firstHitText).toBe("get_sign");
  });
});
