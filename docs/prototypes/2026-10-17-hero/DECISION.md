# 决定：首页 hero = 变体 B（业主 2026-10-17，#231）

**选定 B · 就地展开。** A（交给右下角 dock）与 C（专注模式）未选。

- 未交互时 hero 外观与线上一致（像素门不变）。
- 打字回车 / 发送 / 胶囊 / 拍照 / 附件 / 语音之后：眉题、标题、副标题、胶囊、脚注收起，输入框原地长成对话区，回答与产品卡（桌面四列、手机两列）就在 hero 里；输入框变成追问框；顶部"Genie - Linker's AI assistant"＋"Continue in the side panel"＋关闭。
- 滚出 hero 后右下角出现"继续对话"入口，接到 dock；hero 与 dock 是同一个会话；关闭对话区则 hero 复原。

本目录的代码是**一次性原型**（脚本回答、底部切换条），不进生产；实现票 #232 用真实 Genie，并把首页 hero 作为入口写进 `docs/specs/13-genie.md`。拍照 / 附件依 #236（deepseek-flash 收图；PDF 先转文字或页面图片，见 `docs/research/2026-10-17-deepseek-flash-vision/`）。截图：`screens/hero-B-saj-1440.png`、`screens/hero-B-scrolled-1440.png`、`screens/hero-B-390.png`。
