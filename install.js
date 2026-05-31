#!/usr/bin/env node

const { spawnSync } = require('child_process');
const os = require('os');
const path = require('path');
const fs = require('fs');

const VENV_DIR = path.join(os.homedir(), '.ssh-licco-venv');

function checkAnaconda(pythonCmd) {
    try {
        const result = spawnSync(pythonCmd, ['-c',
            'import sys; print("anaconda" in sys.version.lower() or "conda" in sys.version.lower() or "miniconda" in sys.version.lower())'
        ], {
            encoding: 'utf8',
            stdio: 'pipe',
            shell: process.platform === 'win32'
        });
        if (result.status === 0) {
            return result.stdout.trim() === 'True';
        }
    } catch (e) {}

    try {
        const result = spawnSync(pythonCmd, ['-c', 'import sys; print(sys.version)'], {
            encoding: 'utf8',
            stdio: 'pipe',
            shell: process.platform === 'win32'
        });
        if (result.status === 0) {
            const ver = result.stdout.toLowerCase();
            return ver.includes('anaconda') || ver.includes('conda') || ver.includes('miniconda');
        }
    } catch (e) {}

    return false;
}

function resolvePythonFullPath(pythonCmd) {
    if (process.platform !== 'win32') return pythonCmd;
    try {
        const result = spawnSync('where', [pythonCmd], {
            encoding: 'utf8',
            stdio: 'pipe',
            shell: false
        });
        if (result.status === 0) {
            const first = result.stdout.trim().split('\n')[0].trim();
            return first || pythonCmd;
        }
    } catch (e) {}
    return pythonCmd;
}

function diagnosePythonEnvironment() {
    console.log('🔍 Diagnosing Python environment...');

    const pythonCandidates = [];

    if (process.platform === 'win32') {
        const pathPython = resolvePythonFullPath('python');
        const pathPython3 = resolvePythonFullPath('python3');
        const pathPy = resolvePythonFullPath('py');

        const commonPaths = [
            path.join(os.homedir(), 'AppData', 'Local', 'Programs', 'Python', 'Python313', 'python.exe'),
            path.join(os.homedir(), 'AppData', 'Local', 'Programs', 'Python', 'Python312', 'python.exe'),
            path.join(os.homedir(), 'AppData', 'Local', 'Programs', 'Python', 'Python311', 'python.exe'),
            path.join(os.homedir(), 'AppData', 'Local', 'Programs', 'Python', 'Python310', 'python.exe'),
            'C:\\Python313\\python.exe',
            'C:\\Python312\\python.exe',
            'C:\\Python311\\python.exe',
            'C:\\Python310\\python.exe',
        ].filter(p => fs.existsSync(p));

        pythonCandidates.push(...commonPaths);

        if (!checkAnaconda(pathPython)) pythonCandidates.push(pathPython);
        if (!checkAnaconda(pathPython3)) pythonCandidates.push(pathPython3);
        if (!checkAnaconda(pathPy)) pythonCandidates.push(pathPy);
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
                        const condaCheck = checkAnaconda(pythonCmd);

                        if (condaCheck) {
                            console.log(`  ⚠️  ${pythonCmd}: Python ${version} (Anaconda - used as last resort)`);
                            isAnaconda = true;
                            if (selectedPython === null) {
                                selectedPython = pythonCmd;
                                selectedPythonVersion = version;
                            }
                        } else {
                            console.log(`  ✅ ${pythonCmd}: Python ${version}`);
                            selectedPython = pythonCmd;
                            selectedPythonVersion = version;
                            break;
                        }
                    } else {
                        console.log(`  ⚠️  ${pythonCmd}: Python ${version} (too old, needs 3.10+) - skipping`);
                    }
                }
            }
        } catch (e) {}
    }

    if (selectedPython && isAnaconda) {
        console.log('');
        console.log('  ╔══════════════════════════════════════════════════════════╗');
        console.log('  ║  ⚠️  Using Anaconda Python to create isolated venv      ║');
        console.log('  ║  The venv will be fully isolated from Anaconda          ║');
        console.log('  ╚══════════════════════════════════════════════════════════╝');
        console.log('');
    }

    return { pythonCmd: selectedPython, version: selectedPythonVersion, isAnaconda };
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

function venvHasInstallation() {
    const pythonBinary = process.platform === 'win32'
        ? path.join(VENV_DIR, 'Scripts', 'ssh-licco.exe')
        : path.join(VENV_DIR, 'bin', 'ssh-licco');

    if (!fs.existsSync(pythonBinary)) {
        return false;
    }

    const pythonPath = process.platform === 'win32'
        ? path.join(VENV_DIR, 'Scripts', 'python.exe')
        : path.join(VENV_DIR, 'bin', 'python');

    const result = spawnSync(pythonPath, ['-c',
        'from ssh_mcp.server import SSHMCPServer'
    ], {
        encoding: 'utf8',
        stdio: 'pipe',
        shell: process.platform === 'win32'
    });

    return result.status === 0;
}

function main() {
    console.log('='.repeat(60));
    console.log('🚀 ssh-licco Installer');
    console.log('='.repeat(60));

    const { pythonCmd, version, isAnaconda } = getSafePythonCmd();
    const PKG_PATH = path.join(__dirname);

    console.log('\n📦 Package path:', PKG_PATH);
    console.log('🌐 Virtual environment:', VENV_DIR);

    const needsFreshInstall = !venvHasInstallation();

    if (!needsFreshInstall) {
        console.log('\n📦 Existing installation found, performing incremental update...');
    } else if (!fs.existsSync(VENV_DIR)) {
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
    }

    const pipPath = process.platform === 'win32'
        ? path.join(VENV_DIR, 'Scripts', 'pip.exe')
        : path.join(VENV_DIR, 'bin', 'pip');

    console.log('\n📥 Installing/updating ssh-licco...');

    let installResult;
    if (fs.existsSync(path.join(PKG_PATH, 'pyproject.toml'))) {
        console.log('   Installing from source (editable mode)...');
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