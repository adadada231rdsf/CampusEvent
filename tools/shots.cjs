/**
 * 用独立无头浏览器重新生成验收截图（不受 agent 浏览器浮层影响）。
 * 需要先启动服务：python run.py（127.0.0.1:5000）
 * 运行：node tools/shots.cjs
 */
const path = require('path');
const { chromium } = require('C:/Users/alice/.dsh/profiles/desktop/node_modules/playwright-core');

const BASE = 'http://127.0.0.1:5000';
const OUT = path.join(__dirname, '..', 'docs', 'screenshots');
const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';

async function shot(page, name, fullPage = true) {
  await page.waitForTimeout(250);
  await page.screenshot({ path: path.join(OUT, name), fullPage });
  console.log('shot', name);
}

async function login(page, who) {
  await page.goto(BASE + '/login');
  await page.selectOption('select[name="student_id"]', who);
  await Promise.all([page.waitForLoadState('load'), page.click('form button[type="submit"]')]);
}

async function post(page, url) {
  // 直接 POST 表单路由（UI 上被隐藏的场景：重复报名、满员报名）
  await page.evaluate((u) => fetch(u, { method: 'POST', redirect: 'manual', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: '' }), url);
}

(async () => {
  const browser = await chromium.launch({ executablePath: CHROME, headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2, locale: 'zh-CN' });
  const page = await ctx.newPage();

  // ---------- 学生视角 ----------
  await page.goto(BASE + '/login');
  await shot(page, '01-login.png', false);

  await login(page, '2024001');
  await shot(page, '02-activities.png');

  await page.goto(BASE + '/activity/1');
  await shot(page, '03-activity-detail.png');

  await page.goto(BASE + '/activity/3');
  await Promise.all([page.waitForLoadState('load'), page.click('form button.btn-primary')]);
  await shot(page, '04-register-success.png');

  await page.goto(BASE + '/my');
  await shot(page, '05-my-registrations.png');

  await page.goto(BASE + '/messages');
  await shot(page, '06-messages.png');

  await page.goto(BASE + '/messages');
  await shot(page, '07-messages-read.png');

  // 取消报名（C9）
  await page.goto(BASE + '/activity/3');
  await Promise.all([
    page.waitForLoadState('load'),
    page.click('form[action*="/cancel"] button'),
  ]);
  await shot(page, '08-cancel-success.png');

  // ---------- 管理员视角 ----------
  await page.goto(BASE + '/logout');
  await login(page, 'admin');
  await shot(page, '09-admin-activities.png');

  await page.goto(BASE + '/admin/activity/new');
  await shot(page, '10-admin-activity-form.png');

  await page.goto(BASE + '/admin/approvals');
  await shot(page, '11-admin-approvals.png');

  // C8：对已满员活动批准 -> 失败
  await Promise.all([
    page.waitForLoadState('load'),
    page.click('form[action$="/registration/10/approve"] button.btn-primary'),
  ]);
  await shot(page, '12-approve-fail-full.png');

  // C6：批准王五（有座位）-> 成功
  await Promise.all([
    page.waitForLoadState('load'),
    page.click('form[action$="/registration/4/approve"] button.btn-primary'),
  ]);
  await shot(page, '13-approve-success.png');

  // C7：拒绝李四
  await page.fill('form[action$="/registration/5/reject"] input[name="reason"]', '报名材料不完整，请补充后重新申请');
  await Promise.all([
    page.waitForLoadState('load'),
    page.click('form[action$="/registration/5/reject"] button.btn-danger'),
  ]);
  await shot(page, '14-reject-done.png');

  // ---------- 边界：名额已满 / 重复报名 ----------
  await page.goto(BASE + '/logout');
  await login(page, '2024003');
  await post(page, '/activity/1/register');
  await page.goto(BASE + '/activity/1');
  await shot(page, '15-register-full-fail.png');

  await page.goto(BASE + '/logout');
  await login(page, '2024001');
  await post(page, '/activity/1/register');
  await page.goto(BASE + '/activity/1');
  await shot(page, '16-duplicate-fail.png');

  await page.goto(BASE + '/?q=' + encodeURIComponent('讲座'));
  await shot(page, '17-filter-by-name.png');

  await page.goto(BASE + '/activity/999');
  await shot(page, '18-404.png', false);

  // 学生访问管理页 -> 403
  await page.goto(BASE + '/admin/activities');
  await shot(page, '19-forbidden.png', false);

  await browser.close();
  console.log('done');
})().catch((e) => { console.error(e); process.exit(1); });
