#!/usr/bin/env node

const { spawnSync } = require('child_process');
const os = require('os');
const path = require('path');
const fs = require('fs');

const VENV_DIR = path.join(os.homedir(), '.ssh-licco-venv');

function getPythonCmd() {
    if (process.platform === 'win32') {
        return 'python';
    }
    const python3 = spawnSync('which', ['python3']);
    if (python3.status === 0) {
        return 'python3';
    }
    return 'python';
}

const PYTHON_CMD = getPythonCmd();
const PKG_PATH = path.join(__dirname);

console.log('Installing ssh-licco Python package into venv...');
console.log('Venv location:', VENV_DIR);

if (!fs.existsSync(VENV_DIR)) {
    console.log('Creating venv...');
    const result = spawnSync(PYTHON_CMD, ['-m', 'venv', VENV_DIR], { stdio: 'inherit' });
    if (result.status !== 0) {
        console.error('Failed to create venv');
        process.exit(1);
    }
}

const pipPath = process.platform === 'win32' 
    ? path.join(VENV_DIR, 'Scripts', 'pip.exe')
    : path.join(VENV_DIR, 'bin', 'pip');

console.log('Installing ssh-licco from:', PKG_PATH);
const installResult = spawnSync(pipPath, ['install', '-e', PKG_PATH], { stdio: 'inherit' });
if (installResult.status !== 0) {
    console.error('Failed to install ssh-licco');
    process.exit(1);
}

console.log('\n✅ ssh-licco installed successfully!');
console.log('Run: npx ssh-licco');
