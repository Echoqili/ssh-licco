#!/usr/bin/env node
const { spawn } = require('child_process');
const path = require('path');
const os = require('os');
const fs = require('fs');

const VENV_DIR = path.join(os.homedir(), '.ssh-licco-venv');

function getSshLiccoExe() {
  if (process.platform === 'win32') {
    return path.join(VENV_DIR, 'Scripts', 'ssh-licco.exe');
  }
  return path.join(VENV_DIR, 'bin', 'ssh-licco');
}

const sshLicco = getSshLiccoExe();

if (!fs.existsSync(sshLicco)) {
  console.error('ssh-licco venv not found. Run: npm install -g ssh-licco');
  process.exit(1);
}

const child = spawn(sshLicco, [], {
  stdio: 'inherit',
  env: { ...process.env }
});

child.on('exit', (code) => process.exit(code || 0));
child.on('error', (err) => {
  console.error('Failed to start ssh-licco:', err.message);
  process.exit(1);
});
