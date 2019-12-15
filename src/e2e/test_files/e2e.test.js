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
        "KLEE: done: total instructions = 32\n" +
        "KLEE: done: completed paths = 3\n" +
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
