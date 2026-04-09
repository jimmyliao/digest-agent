#!/usr/bin/env node
// BeforeTool Hook: 防止刪除或移動 src/app.py

const chunks = [];
process.stdin.on('data', d => chunks.push(d));
process.stdin.on('end', () => {
  let input = {};
  try { input = JSON.parse(Buffer.concat(chunks).toString()); } catch (_) {}

  const command = input?.tool_input?.command || '';

  if ((command.includes('rm ') || command.includes('mv ')) && command.includes('src/app.py')) {
    process.stderr.write('🛡️ SRE Guardian: src/app.py 是服務核心，禁止刪除或移出原路徑。\n');
    console.log(JSON.stringify({ decision: 'deny', reason: 'src/app.py is protected' }));
    process.exit(1);
  }

  console.log(JSON.stringify({ decision: 'allow' }));
  process.exit(0);
});
