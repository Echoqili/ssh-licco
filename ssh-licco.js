#!/usr/bin/env node

const { spawn, spawnSync } = require('child_process');
const os = require('os');
const path = require('path');
const fs = require('fs');

const VENV_DIR = path.join(os.homedir(), '.ssh-licco-venv');
const AUTO_INSTALL = process.env.SSH_LICCO_AUTO_INSTALL !== 'false';

function diagnosePythonEnvironment() {
    const pythonCandidates = [];
    
    if (process.platform === 'win32') {
        pythonCandidates.push('python');
        pythonCandidates.push('py');
        pythonCandidates.push('python3');
        const commonPaths = [
            path.join(os.homedir(), 'AppData', 'Local', 'Programs', 'Python', 'Python312', 'python.exe'),
            path.join(os.homedir(), 'AppData', 'Local', 'Programs', 'Python', 'Python311', 'python.exe'),
            path.join(os.homedir(), 'AppData', 'Local', 'Programs', 'Python', 'Python310', 'python.exe'),
            'C:\\Python312\\python.exe',
            'C:\\Python311\\python.exe',
            'C:\\Python310\\python.exe',
        ];
        commonPaths.forEach(p => {
            if (fs.existsSync(p)) {
                pythonCandidates.push(p);
            }
        });
    } else {
        pythonCandidates.push('python3');
        pythonCandidates.push('python');
    }
    
    let selectedPython = null;
    
    for (const pythonCmd of pythonCandidates) {
        try {
            const result = spawnSync(pythonCmd, ['--version'], { 
                encoding: 'utf8',
                stdio: 'pipe',
                shell: process.platform === 'win32'
            });
            
            if (result.status === 0) {
                const versionOutput = (result.stdout || result.stderr || '').trim();
                const versionMatch = versionOutput.match(/Python (\d+\.\d+\.\d+)/);
                
                if (versionMatch) {
                    const [major, minor] = versionMatch[1].split('.').map(Number);
                    if (major >= 3 && minor >= 10) {
                        selectedPython = pythonCmd;
                        break;
                    }
                }
            }
        } catch (e) {
            // 继续尝试
        }
    }
    
    return selectedPython;
}

function autoInstall() {
    console.error('🤖 ssh-licco not found, starting auto-install...');
    
    const pythonCmd = diagnosePythonEnvironment();
    
    if (!pythonCmd) {
        console.error('❌ No suitable Python interpreter found (needs Python 3.10+)');
        console.error('   Please install Python 3.10 or higher');
        process.exit(1);
    }
    
    const PKG_PATH = path.join(__dirname);
    
    console.error('📦 Creating isolated virtual environment...');
    if (!fs.existsSync(VENV_DIR)) {
        const result = spawnSync(pythonCmd, ['-m', 'venv', VENV_DIR], { 
            stdio: 'inherit',
            shell: process.platform === 'win32'
        });
        if (result.status !== 0) {
            console.error('❌ Failed to create venv');
            return false;
        }
    }
    
    const pipPath = process.platform === 'win32' 
        ? path.join(VENV_DIR, 'Scripts', 'pip.exe')
        : path.join(VENV_DIR, 'bin', 'pip');
    
    console.error('📥 Installing ssh-licco...');
    let installResult;
    if (fs.existsSync(path.join(PKG_PATH, 'pyproject.toml'))) {
        installResult = spawnSync(pipPath, ['install', '-e', PKG_PATH], { 
            stdio: 'inherit',
            shell: process.platform === 'win32'
        });
    } else {
        installResult = spawnSync(pipPath, ['install', 'ssh-licco'], { 
            stdio: 'inherit',
            shell: process.platform === 'win32'
        });
    }
    
    if (installResult.status !== 0) {
        console.error('❌ Failed to install ssh-licco');
        return false;
    }
    
    console.error('✅ ssh-licco installed successfully!');
    return true;
}

function getPythonBinary() {
    if (process.platform === 'win32') {
        return path.join(VENV_DIR, 'Scripts', 'ssh-licco.exe');
    }
    return path.join(VENV_DIR, 'bin', 'ssh-licco');
}

const pythonBinary = getPythonBinary();

if (!fs.existsSync(pythonBinary)) {
    if (AUTO_INSTALL) {
        if (!autoInstall()) {
            process.exit(1);
        }
        // 重新检查二进制文件是否存在
        if (!fs.existsSync(pythonBinary)) {
            console.error('❌ Auto-install completed but binary still not found');
            process.exit(1);
        }
    } else {
        console.error('Error: ssh-licco not installed in venv.');
        console.error('Please run: npm install -g ssh-licco');
        console.error('Or set SSH_LICCO_AUTO_INSTALL=true to enable auto-install');
        process.exit(1);
    }
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
