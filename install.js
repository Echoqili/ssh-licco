#!/usr/bin/env node

const { spawnSync, execSync } = require('child_process');
const os = require('os');
const path = require('path');
const fs = require('fs');

const VENV_DIR = path.join(os.homedir(), '.ssh-licco-venv');

function diagnosePythonEnvironment() {
    console.log('🔍 Diagnosing Python environment...');
    console.log('  • Platform:', process.platform);
    console.log('  • Home directory:', os.homedir());
    
    // 检测 Python 候选列表
    const pythonCandidates = [];
    
    if (process.platform === 'win32') {
        pythonCandidates.push('python');
        pythonCandidates.push('py');
        pythonCandidates.push('python3');
        // 添加常见的 Python 安装路径
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
        pythonCandidates.push('/usr/bin/python3');
        pythonCandidates.push('/usr/local/bin/python3');
    }
    
    let selectedPython = null;
    let selectedPythonVersion = null;
    let isAnaconda = false;
    
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
                    const version = versionMatch[1];
                    const [major, minor] = version.split('.').map(Number);
                    
                    if (major >= 3 && minor >= 10) {
                        // 检测是否是 Anaconda
                        const condaCheck = checkAnaconda(pythonCmd);
                        
                        if (condaCheck) {
                            console.log(`  ⚠️  Found ${pythonCmd}: Python ${version} (Anaconda - will use isolated venv)`);
                            isAnaconda = true;
                        } else {
                            console.log(`  ✅ Found ${pythonCmd}: Python ${version}`);
                        }
                        
                        selectedPython = pythonCmd;
                        selectedPythonVersion = version;
                        break;
                    } else {
                        console.log(`  ⚠️  ${pythonCmd}: Python ${version} (too old, needs 3.10+) - skipping`);
                    }
                }
            }
        } catch (e) {
            // 继续尝试下一个
        }
    }
    
    return { pythonCmd: selectedPython, version: selectedPythonVersion, isAnaconda };
}

function checkAnaconda(pythonCmd) {
    try {
        const result = spawnSync(pythonCmd, ['-c', 'import sys; print("anaconda" in sys.version.lower() or "conda" in sys.version.lower() or "miniconda" in sys.version.lower())'], { 
            encoding: 'utf8',
            stdio: 'pipe',
            shell: process.platform === 'win32'
        });
        
        if (result.status === 0) {
            return result.stdout.trim() === 'True';
        }
    } catch (e) {
        // 忽略错误
    }
    
    // 备用检测方法
    try {
        const result = spawnSync(pythonCmd, ['-c', 'import sys; print(sys.version)'], { 
            encoding: 'utf8',
            stdio: 'pipe',
            shell: process.platform === 'win32'
        });
        
        if (result.status === 0) {
            const version = result.stdout.toLowerCase();
            return version.includes('anaconda') || version.includes('conda') || version.includes('miniconda');
        }
    } catch (e) {
        // 忽略错误
    }
    
    return false;
}

function getSafePythonCmd() {
    const diagnosis = diagnosePythonEnvironment();
    
    if (!diagnosis.pythonCmd) {
        console.error('\n❌ No suitable Python interpreter found (needs Python 3.10+)');
        console.error('   Please install Python 3.10 or higher from https://python.org');
        console.error('   Make sure to check "Add Python to PATH" during installation');
        process.exit(1);
    }
    
    return diagnosis;
}

function main() {
    console.log('='.repeat(60));
    console.log('🚀 ssh-licco Installer');
    console.log('='.repeat(60));
    
    const { pythonCmd, version, isAnaconda } = getSafePythonCmd();
    const PKG_PATH = path.join(__dirname);
    
    console.log('\n📦 Package path:', PKG_PATH);
    console.log('🌐 Virtual environment:', VENV_DIR);
    
    // 检查是否需要清理旧环境
    if (fs.existsSync(VENV_DIR)) {
        console.log('\n🗑️  Cleaning up old environment...');
        try {
            fs.rmSync(VENV_DIR, { recursive: true, force: true });
            console.log('   ✅ Old environment cleaned');
        } catch (e) {
            console.log('   ⚠️  Could not clean old environment, will try to continue');
        }
    }
    
    console.log('\n🔧 Creating isolated virtual environment...');
    if (isAnaconda) {
        console.log('   This ensures no conflicts with your Anaconda installation');
    } else {
        console.log('   This avoids conflicts with your system Python');
    }
    
    const venvResult = spawnSync(pythonCmd, ['-m', 'venv', VENV_DIR], { 
        stdio: 'inherit',
        shell: process.platform === 'win32'
    });
    
    if (venvResult.status !== 0) {
        console.error('\n❌ Failed to create virtual environment');
        console.error('   Please check your Python installation and try again');
        process.exit(1);
    }
    console.log('   ✅ Virtual environment created successfully');
    
    const pipPath = process.platform === 'win32' 
        ? path.join(VENV_DIR, 'Scripts', 'pip.exe')
        : path.join(VENV_DIR, 'bin', 'pip');
    
    console.log('\n📥 Installing ssh-licco into isolated environment...');
    
    // 尝试从源码安装（如果是开发版本），否则从 PyPI 安装
    let installResult;
    if (fs.existsSync(path.join(PKG_PATH, 'pyproject.toml'))) {
        console.log('   Installing from source...');
        installResult = spawnSync(pipPath, ['install', '-e', PKG_PATH], { 
            stdio: 'inherit',
            shell: process.platform === 'win32'
        });
    } else {
        console.log('   Installing from PyPI...');
        installResult = spawnSync(pipPath, ['install', 'ssh-licco'], { 
            stdio: 'inherit',
            shell: process.platform === 'win32'
        });
    }
    
    if (installResult.status !== 0) {
        console.error('\n❌ Failed to install ssh-licco');
        process.exit(1);
    }
    
    console.log('\n' + '='.repeat(60));
    console.log('✅ ssh-licco installed successfully!');
    console.log('='.repeat(60));
    console.log('\n📖 Quick Start:');
    console.log('   • Run: npx ssh-licco');
    console.log('   • Or add to your mcp.config.json');
    console.log('\n🔒 Isolation Note:');
    console.log('   • ssh-licco runs in a dedicated virtual environment');
    if (isAnaconda) {
        console.log('   • No conflicts with your Anaconda installation');
    } else {
        console.log('   • No conflicts with your system Python');
    }
    console.log('='.repeat(60));
}

main();
