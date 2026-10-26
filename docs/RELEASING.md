# 发布与失败恢复

使用现有 `.github/workflows/pypi.yml` 作为发布入口。`auto-release.yml` 是该入口调用的
复用任务，不再独立监听标签，因此 GitHub Release 不会抢在测试或 PyPI 验证之前创建。
不需要 npm 账号，也不会执行 `npm publish`。Node 安装包作为 GitHub Release 附件提供。

## 准备新版本

在独立分支修改代码并同步版本，例如：

```powershell
python sync_version.py 2.8.1 --no-commit --no-tag
python sync_version.py --check
python -m pytest tests -q
node --test tests/install.test.cjs
```

检查变更、提交并合并到 master 后，为通过检查的提交创建标签：

```powershell
git switch master
git pull --ff-only github master
git tag -a v2.8.1 -m "Release 2.8.1"
git push github v2.8.1
```

推送 `vX.Y.Z` 标签会开始正式发布。标签必须已经存在且与 VERSION 及其他版本源一致，
工作流将标签解析成固定提交 SHA 后构建，发布期间不会改文件、自动提交或移动标签。

## 自动执行顺序

1. 解析标签，检查 VERSION、Python/npm 元数据及文档的版本一致性。
2. 运行 Python 与 Node 回归测试、构建 wheel/sdist 和 npm tarball，检查包元数据。
3. 在独立虚拟环境安装本地 wheel，逐文件核对包内 Python 源码与标签源码。
4. 查询官方 PyPI。只上传缺失的 wheel/sdist；网络故障、异常响应会停止发布。
5. 从官方 PyPI 全新安装指定版本，再次核对所有包内 Python 源码。
6. 保存构建产物。通过复用工作流创建 Release 草稿、补齐附件，再公开 Release。
   已有 wheel、源码包和 npm tarball 不覆盖；SHA256SUMS 根据实际附件生成。

同版本发布任务排队执行，不会因新的运行而中断正在进行的上传。
各次运行的 Summary 会列出标签、源提交、是否请求上传及缺失的 PyPI 文件数。

## 只验证已有标签

在 GitHub Actions 中选择发布入口，填入标签，保持 `publish=false`。
或运行：

```powershell
gh workflow run pypi.yml --repo Echoqili/ssh-licco --ref master -f release_ref=v2.8.0 -F publish=false
```

此模式执行测试、构建、隔离安装和 PyPI 状态查询，并保存验证产物；不会上传 PyPI、
创建/修改 GitHub Release 或调用 MCP Registry。默认手动运行采用此模式。

## 恢复失败的发布

修复工作流后，使用最新 master 上的工作流处理原标签，不改原标签、不创建重复版本：

```powershell
gh workflow run pypi.yml --repo Echoqili/ssh-licco --ref master -f release_ref=v2.8.0 -F publish=true
```

工作流控制脚本来自所选工作流提交，产品代码来自原标签，因此即使老标签没有新的恢复脚本，
也能使用当前流程恢复。已有 PyPI 文件跳过，缺失文件继续上传；PyPI 完整时只核验公开安装，
然后补齐 GitHub Release 附件。原有失败记录仍会保留，查看最新恢复任务的状态即可。

若该版本在 PyPI 的代码与标签源码不同，流程会失败。PyPI 同版本文件不可覆盖，
此时应修正源码并发新版本，而不是移动旧标签。

## 凭据与 MCP Registry

- GitHub 操作使用自动提供的 `github.token`，不依赖个人 `MCP_GITHUB_TOKEN`。
- PyPI 使用现有仓库 Secret `PYPI_API_TOKEN`；未设置时，上传 Action 使用 PyPI Trusted
  Publishing，需事先在 PyPI 配置仓库、workflow 文件和发布权限。两者至少有一种可用。
- Token 不得提交到仓库或写入日志。MCP Registry 的认证/错误响应体也不会输出。
- MCP Registry 是独立的可选步骤，默认关闭。确认该仓库的 Registry 身份有发布权限后，
  手动恢复命令可增加 `-F publish_registry=true`；同时必须有 `publish=true`。
  Registry 失败会明确显示为失败，不再用 `continue-on-error` 掩盖。
  此步骤失败不会回滚已经发布的 PyPI 或 GitHub Release。

## 用户安装

```powershell
pip install --upgrade ssh-licco==2.8.0
npm install -g https://github.com/Echoqili/ssh-licco/releases/download/v2.8.0/ssh-licco-2.8.0.tgz
```

两个命令都是公开下载，不需要 npm 登录。用户可用 Release 中的 SHA256SUMS 校验附件。
