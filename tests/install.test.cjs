const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

for (const filename of ['install.js', 'ssh-licco.js']) {
  test(`${filename} preserves Windows paths with spaces`, () => {
    const calls = [];
    let created = false;
    const children = {
      spawnSync(command, args, options) {
        calls.push({ command, args, options });
        // cmd.exe splits unquoted arguments; launching the executable directly
        // must preserve each argument, including a path containing spaces.
        if (options.shell && args.some(arg => /\s/.test(arg))) {
          return { status: 1, stdout: '', stderr: 'argument was split by shell' };
        }
        if (args[0] === '--version') return { status: 0, stdout: 'Python 3.12.13' };
        if (args[0] === '-c') return { status: 0, stdout: 'False' };
        if (args[0] === '-m' && args[1] === 'venv') created = true;
        return { status: 0, stdout: '', stderr: '' };
      },
      spawn(command, args, options) {
        calls.push({ command, args, options });
        return { on() {} };
      },
    };
    const fakeFs = {
      existsSync(filename) {
        if (filename.endsWith('pyproject.toml')) return true;
        return created && filename.endsWith('python.exe');
      },
    };
    vm.runInNewContext(fs.readFileSync(path.join(__dirname, '..', filename), 'utf8'), {
      require(name) {
        if (name === 'child_process') return children;
        if (name === 'os') return { homedir: () => 'C:\\test user home' };
        if (name === 'path') return path.win32;
        if (name === 'fs') return fakeFs;
        throw new Error(`Unexpected module ${name}`);
      },
      __dirname: 'C:\\test install folder\\ssh-licco',
      console: { log() {}, error() {} },
      process: {
        platform: 'win32', env: {}, argv: ['node', filename],
        exit(code) { throw new Error(`Installer exited with ${code}`); },
      },
    });
    const install = calls.find(call => call.args[0] === 'install');
    assert.ok(install, 'installation was attempted');
    assert.equal(install.args[2], 'C:\\test install folder\\ssh-licco');
    assert.equal(install.options.shell, false);
  });
}
