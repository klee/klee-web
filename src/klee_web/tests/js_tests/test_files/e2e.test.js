const puppeteer = require('puppeteer');

jest.setTimeout(15000);

describe('Input', () => {
  beforeAll(async () => {

    await page.goto('http://localhost/');
    await page.waitForSelector('[ng-repeat="file in files"]');
    await page.click('[ng-repeat="file in files"]');  // select first file ... use page.select instead?
    await page.click('#run-klee-btn');
    await page.waitForSelector('#result-output');
  });
  it('tests that input files are processed correctly', async () => {

    const text = await page.evaluate(() => document.querySelector('#result-output').innerText);
    await expect(text).toMatch(
      'KLEE: output directory is "/tmp/code/klee-out-0"\n' + 
      'KLEE: Using STP solver backend\n\n' + 
      'KLEE: done: total instructions = 32\n' +
      'KLEE: done: completed paths = 3\n' + 
      'KLEE: done: generated tests = 3');
  });
});

describe('Admin', () => {
  beforeAll(async () => {

    await page.goto('http://localhost/admin');
    await page.waitForSelector('#id_username');
    await page.type('#id_username', 'admin');
    await page.type('#id_password', 'development');
    await Promise.all([page.click('[type=submit]'), page.waitForNavigation()]);
  });
  it('tests that the admin can login', async () => {
    var title = await page.title();
    await expect(title).toMatch("Site administration | Django site admin");
  });
});

describe('New Projects', () => {
  beforeAll(async () => {

    await page.goto('http://localhost/user/login');
    await page.type('[type=text]', 'admin');
    await page.type('[type=password]', 'development');
    await Promise.all([page.click('[type=submit]'), page.waitForNavigation()]);
  });
  it('tests that logged users can add new projects', async () => {
    var content = await page.content();
    await expect(content).toMatch("Add New Project");
  });
});
