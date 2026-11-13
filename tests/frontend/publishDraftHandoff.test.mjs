import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { runInNewContext } from 'node:vm';
import { test } from 'node:test';

const require = createRequire(new URL('../../web/frontend/package.json', import.meta.url));
const ts = require('typescript');
const compile = source => ts.transpileModule(source, {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS },
}).outputText;

const handoffExports = {};
runInNewContext(compile(readFileSync(new URL('../../web/frontend/src/lib/publishHandoff.ts', import.meta.url), 'utf8')), { exports: handoffExports });
const { draftFromReply } = handoffExports;

test('labelled copy excludes planning and review notes, while ambiguous replies stay intact', () => {
  const draft = draftFromReply('先读取画像。\n## 标题\n早产宝宝投保前核对\n## 正文\n先整理已有记录。\n\n再看健康告知。\n## 话题建议\n#宝宝保险 #健康告知\n---\n审核备注：待专业审核\n本地初稿：outputs/稿件.md');
  assert.equal(draft.title, '早产宝宝投保前核对');
  assert.equal(draft.body, '先整理已有记录。\n\n再看健康告知。');
  assert.equal(draft.tags, '宝宝保险,健康告知');
  const ambiguous = '## 标题\n1. 选项一\n2. 选项二\n## 正文\n正文';
  assert.equal(draftFromReply(ambiguous).body, ambiguous);
  assert.equal(draftFromReply('普通未分段的回复').body, '普通未分段的回复');
});

test('IP drafts preserve media across reloads without borrowing another IP or legacy draft', () => {
  const entries = new Map([['easel_publish_draft', JSON.stringify({ title: '旧草稿', body: '保留原稿' })]]);
  const localStorage = { getItem: key => entries.get(key) ?? null, setItem: (key, value) => entries.set(key, value) };
  const source = readFileSync(new URL('../../web/frontend/src/lib/store.ts', import.meta.url), 'utf8');
  const loadModule = () => {
    const exports = {};
    runInNewContext(compile(source), { exports, localStorage, Date, Math });
    return exports;
  };
  const draft = { title: '宝宝保险', body: '真实待审核稿', platforms: ['xiaohongshu'], overrides: {}, tags: '宝宝保险', selectedMedia: ['学霸慧慧/封面.png'] };
  loadModule().savePublishDraft(draft, '学霸慧慧');
  const reloaded = loadModule();
  assert.equal(JSON.stringify(reloaded.loadPublishDraft('学霸慧慧')), JSON.stringify(draft));
  assert.equal(reloaded.loadPublishDraft('其他IP').body, '');
  assert.equal(reloaded.loadPublishDraft().body, '保留原稿');
  reloaded.savePublishDraft({ ...draft, body: '另一个账号的文案', selectedMedia: [] }, '其他IP');
  assert.equal(reloaded.loadPublishDraft('学霸慧慧').body, draft.body);
  assert.equal(reloaded.loadPublishDraft('其他IP').body, '另一个账号的文案');
});

test('chat handoff keeps original text and current IP; cancelling replacement leaves draft untouched', () => {
  const source = readFileSync(new URL('../../web/frontend/src/App.tsx', import.meta.url), 'utf8');
  const ast = ts.createSourceFile('App.tsx', source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  let declaration;
  function visit(node) {
    if (ts.isVariableDeclaration(node) && node.name.getText(ast) === 'handlePreparePublish') declaration = node.getText(ast);
    ts.forEachChild(node, visit);
  }
  visit(ast);
  assert.ok(declaration);
  const writes = [], pages = [];
  let allowReplace = false;
  const context = {
    useCallback: callback => callback,
    selectedPersona: '学霸慧慧',
    draftFromReply,
    loadPublishDraft: () => ({ title: '已有草稿', body: '已有正文' }),
    savePublishDraft: (...args) => writes.push(args),
    setCurrentPage: page => pages.push(page),
    window: { confirm: () => allowReplace },
  };
  runInNewContext(compile(`const ${declaration}; globalThis.handoff = handlePreparePublish;`), context);
  context.handoff('新的待审核回复');
  assert.equal(writes.length, 0);
  assert.equal(pages.length, 0);
  allowReplace = true;
  context.handoff('新的待审核回复');
  assert.equal(writes[0][0].body, '新的待审核回复');
  assert.equal(writes[0][1], '学霸慧慧');
  assert.equal(pages[0], 'publish');
  context.handoff('  ');
  assert.equal(writes.length, 1);
});
