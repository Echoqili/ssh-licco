#!/usr/bin/env node
const { execSync } = require('child_process');
const path = require('path');
const os = require('os');
const fs = require('fs');

const VENV_DIR = path.join(os.homedir(), '.ssh-licco-venv');

function findPython() {
  const candidates = process.platform === 'win32'
    ? ['python', 'python3', 'C:\\software\\anaconda\\python.exe']
    : ['python3', 'python'];

  for (const cmd of candidates) {
    try {
      const ver = execSync(`${cmd} --version`, { encoding: 'utf8', stdio: ['pipe', 'pipe', 'pipe'] }).trim();
      if (ver.includes('Python 3')) {
        console.log(`Found Python: ${cmd} (${ver})`);
        return cmd;
      }
    } catch {}
  }
  return null;
}

function main() {
  console.log('Setting up ssh-licco isolated environment...');

  const python = findPython();
  if (!python) {
    console.error('ERROR: Python 3 not found. Please install Python 3.10+ first.');
    process.exit(1);
  }

  if (fs.existsSync(VENV_DIR)) {
    console.log('Venv already exists, removing old one...');
    fs.rmSync(VENV_DIR, { recursive: true, force: true });
  }

  console.log(`Creating venv at ${VENV_DIR}...`);
  execSync(`"${python}" -m venv "${VENV_DIR}"`, { stdio: 'inherit' });

  const pip = process.platform === 'win32'
    ? path.join(VENV_DIR, 'Scripts', 'pip.exe')
    : path.join(VENV_DIR, 'bin', 'pip');

  console.log('Installing ssh-licco from PyPI...');
  execSync(`"${pip}" install ssh-licco`, { stdio: 'inherit' });

  console.log('\nssh-licco installed successfully!');
  console.log('You can now use: npx ssh-licco');
}

main();
