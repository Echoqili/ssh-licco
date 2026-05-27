#!/usr/bin/env node

const { spawn } = require('child_process');
const os = require('os');
const path = require('path');
const fs = require('fs');

const VENV_DIR = path.join(os.homedir(), '.ssh-licco-venv');

function getPythonBinary() {
    if (process.platform === 'win32') {
        return path.join(VENV_DIR, 'Scripts', 'ssh-licco.exe');
    }
    return path.join(VENV_DIR, 'bin', 'ssh-licco');
}

const pythonBinary = getPythonBinary();

if (!fs.existsSync(pythonBinary)) {
    console.error('Error: ssh-licco not installed in venv.');
    console.error('Please run: npm install -g ssh-licco');
    process.exit(1);
}

const proc = spawn(pythonBinary, process.argv.slice(2), {
    stdio: 'inherit',
    env: process.env
});

proc.on('error', (err) => {
    console.error('Failed to start ssh-licco:', err);
    process.exit(1);
});

proc.on('exit', (code) => {
    process.exit(code || 0);
});
