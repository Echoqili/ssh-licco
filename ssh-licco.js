#!/usr/bin/env node

const { spawn, spawnSync } = require('child_process');
const os = require('os');
const path = require('path');
const fs = require('fs');

const VENV_DIR = path.join(os.homedir(), '.ssh-licco-venv');
const AUTO_INSTALL = process.env.SSH_LICCO_AUTO_INSTALL !== 'false';

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
                        if (checkAnaconda(pythonCmd)) {
                            console.error(`  ⚠️  Found ${pythonCmd}: Python ${versionMatch[1]} (Anaconda - used as last resort)`);
                            if (selectedPython === null) {
                                selectedPython = pythonCmd;
                            }
                        } else {
                            selectedPython = pythonCmd;
                            break;
                        }
                    }
                }
            }
        } catch (e) {}
    }

    if (selectedPython && checkAnaconda(selectedPython)) {
        console.error('');
        console.error('  ╔══════════════════════════════════════════════════════════╗');
        console.error('  ║  ⚠️  Using Anaconda Python to create isolated venv      ║');
        console.error('  ║  The venv at ~/.ssh-licco-venv will be fully isolated  ║');
        console.error('  ║  No conflicts with your Anaconda installation          ║');
        console.error('  ╚══════════════════════════════════════════════════════════╝');
        console.error('');
    }

    return selectedPython;
}

function verifyIntegrity() {
    const pythonPath = process.platform === 'win32'
        ? path.join(VENV_DIR, 'Scripts', 'python.exe')
        : path.join(VENV_DIR, 'bin', 'python');

    const result = spawnSync(pythonPath, ['-c',
        'from ssh_mcp.server import SSHMCPServer; from ssh_mcp.session_manager import SessionManager'
    ], {
        encoding: 'utf8',
        stdio: 'pipe',
        shell: false
    });

    return result.status === 0;
}

function autoInstall(forceReinstall) {
    if (forceReinstall) {
        console.error('🔧 Dependency integrity check failed, repairing installation...')
    } else {
        console.error('🤖 ssh-licco not found, starting auto-install...');
    }

    const pythonCmd = diagnosePythonEnvironment();

    if (!pythonCmd) {
        console.error('❌ No suitable Python interpreter found (needs Python 3.10+)');
        console.error('   Please install Python 3.10 or higher');
        process.exit(1);
    }

    const PKG_PATH = path.join(__dirname);

    if (!fs.existsSync(VENV_DIR)) {
        console.error('📦 Creating isolated virtual environment...');
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

function checkGlobalCommand() {
    if (process.platform !== 'win32') return;
    try {
        const result = spawnSync('where', ['ssh-licco'], {
            encoding: 'utf8',
            stdio: 'pipe',
            shell: false
        });
        if (result.status === 0 && result.stdout) {
            const entries = result.stdout.trim().split(/\r?\n/).map(s => s.trim()).filter(Boolean);
            if (entries.length > 1) {
                console.error('  ⚠️  Multiple ssh-licco installations found:');
                entries.forEach(e => console.error(`     ${e}`));
                const nodeGlobal = entries.find(e => e.includes('node_global') || e.includes('npm'));
                const anacondaPath = entries.find(e => e.toLowerCase().includes('anaconda'));
                if (anacondaPath && nodeGlobal) {
                    console.error('  ⚠️  Anaconda entry takes priority over npm in PATH');
                    console.error('  💡  Move node_global before Anaconda in your PATH');
                }
                console.error('');
            }
            const firstEntry = entries[0] || '';
            if (firstEntry.toLowerCase().includes('anaconda')) {
                console.error('  ╔══════════════════════════════════════════════════════════╗');
                console.error('  ║  ⚠️  ssh-licco resolves to Anaconda, not npm!           ║');
                console.error('  ║  This may cause environment conflicts.                 ║');
                console.error('  ║  Fix: Move node_global before Anaconda in PATH         ║');
                console.error('  ╚══════════════════════════════════════════════════════════╝');
                console.error('');
            }
        }
    } catch (e) {}
}

const pythonBinary = getPythonBinary();
checkGlobalCommand();

if (!fs.existsSync(pythonBinary)) {
    if (AUTO_INSTALL) {
        if (!autoInstall(false)) {
            process.exit(1);
        }
    } else {
        console.error('Error: ssh-licco not installed in venv.');
        console.error('Please run: npm install -g ssh-licco');
        console.error('Or set SSH_LICCO_AUTO_INSTALL=true to enable auto-install');
        process.exit(1);
    }
} else if (!verifyIntegrity()) {
    if (AUTO_INSTALL) {
        if (!autoInstall(true)) {
            process.exit(1);
        }
    } else {
        console.error('Error: ssh-licco dependencies are incomplete.');
        console.error('Set SSH_LICCO_AUTO_INSTALL=true to enable auto-repair');
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