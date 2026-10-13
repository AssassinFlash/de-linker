"""Generate the measured target table from Playwright's raw JSON."""
from pathlib import Path
import json
P = Path(__file__).resolve().parent
REF = json.loads((P/'measurements-ref.json').read_text())
OURS = json.loads((P/'measurements-ours.json').read_text())
BASE = json.loads((P/'measurements-baseline.json').read_text())
def value(data, page, probe, prop):
    obj = data[page]['probes'].get(probe)
    if obj is None: return 'not present'
    for key in prop.split('.'): obj = obj.get(key) if isinstance(obj, dict) else None
    return f'{obj:.2f}' if isinstance(obj, float) else str(obj)
def row(label, refpage, refprobe, prop, ourpage, ourprobe, note=''):
    return f'| {label} | {value(REF,refpage,refprobe,prop)} | {value(OURS,ourpage,ourprobe,prop)} | {note} |'
lines = ['# 目标值 vs 实现值（真实 computed style / rect）', '',
 '量测：`measure.mjs`；参照=file:// Preline Pro，本地=t110 登录态；1440×900、390×844、430×932。',
 '原始数据保留在 measurements-ref.json / measurements-baseline.json / measurements-ours.json / measurements-ours-de.json；null 表示无对应元素，不以猜值补齐。', '',
 '## 桌面尺度：现状 → 参照目标 → 采用值', '',
 '| 维度 | 接续前序现状 | 参照目标 | 最终实现 | 采用理由 |','|---|---|---|---|---|']
for label, probe, prop, refpage, refprobe, note in [
 ('工作区宽度','workspace','rect.width','ref-account-profile-1440','workspace','全宽工作台，不再锁 1240'),
 ('主内容宽度','content','rect.width','ref-account-profile-1440','card','260 侧栏 + 20 gap + 两侧 20；与参照 1140 相差 20'),
 ('左侧栏宽度','sidebar','rect.width','ref-account-profile-1440','sidebar','精确 260'),
 ('页面标题字号','h1','fontSize','ref-account-profile-1440','h1','业主要求抬高存在感，主动采用 32 而非 18'),
 ('页面标题字重','h1','fontWeight','ref-account-profile-1440','h1','600'),
 ('页面标题行高','h1','lineHeight','ref-account-profile-1440','h1','消费 leading-title，随 32 字号放大'),
 ('瓦片宽','tile','rect.width','ref-crm-index-1440','tile','参照无侧栏；我们保留侧栏后四列 265'),
 ('瓦片高','tile','rect.height','ref-crm-index-1440','tile','精确 146'),
 ('瓦片间距','tiles.grid','gap','ref-crm-index-1440','tiles.grid','精确 20'),
 ('瓦片内边距','tile','padding','ref-crm-index-1440','tile','精确 20'),
 ('瓦片圆角','tile','borderRadius','ref-crm-index-1440','tile','精确 16'),
]:
 lines.append(f'| {label} | {value(BASE,"ours-overview-1440",probe,prop)} | {value(REF,refpage,refprobe,prop)} | {value(OURS,"ours-overview-1440",probe,prop)} | {note} |')
lines += ['', '## 桌面形制与皮肤', '', '| 元素/属性 | Preline 实测 | 我们实测 | 说明 |','|---|---|---|---|']
for args in [
 ('卡片圆角','ref-overview-1440','card','borderRadius','ours-overview-1440','card','12px'),
 ('卡片边框宽','ref-overview-1440','card','borderWidth','ours-overview-1440','card','1px'),
 ('卡片背景','ref-overview-1440','card','backgroundColor','ours-overview-1440','card','proto-canvas-white'),
 ('卡片边框色','ref-overview-1440','card','borderColor','ours-overview-1440','card','proto-neutral-200'),
 ('卡片阴影','ref-overview-1440','card','boxShadow','ours-overview-1440','card','保留 proto-shadow-1，不新造色值'),
 ('卡片标题字号','ref-overview-1440','card.heading','fontSize','ours-overview-1440','card.heading',''),
 ('卡片标题字重','ref-overview-1440','card.heading','fontWeight','ours-overview-1440','card.heading',''),
 ('表格单元内边距','ref-inquiries-1440','table.td','padding','ours-inquiries-1440','table.td','12px 16px'),
 ('表格行高','ref-inquiries-1440','table.row','rect.height','ours-inquiries-1440','table.row','真实商品副行+三个动作，高于单行姓名表；不删信息凑高度'),
 ('表头字体','ref-posts-1440','table.th-inner','fontSize','ours-documents-1440','table.th','CMS 12px uppercase 形制'),
 ('表头字色','ref-posts-1440','table.th-inner','color','ours-documents-1440','table.th','proto-neutral-500'),
 ('正文行高','ref-inquiries-1440','table.td','lineHeight','ours-inquiries-1440','table.td','我们继承 proto-leading-title'),
 ('徽章圆角','ref-documents-1440','badge.paid','borderRadius','ours-overview-1440','badge','6px 桌面'),
 ('徽章内边距','ref-documents-1440','badge.paid','padding','ours-overview-1440','badge','4px 8px'),
 ('徽章字号','ref-documents-1440','badge.paid','fontSize','ours-overview-1440','badge','12px'),
 ('输入高度','ref-account-profile-1440','form.input','rect.height','ours-company-1440','form.input','38px 桌面，48px 移动'),
 ('输入圆角','ref-account-profile-1440','form.input','borderRadius','ours-company-1440','form.input','8px'),
 ('输入边框宽','ref-account-profile-1440','form.input','borderWidth','ours-company-1440','form.input','1px'),
 ('表单卡内边距','ref-account-profile-1440','card','padding','ours-company-1440','form.card','32px'),
 ('区块间距','ref-overview-1440','content','gap','ours-overview-1440','sections.gap','我们使用 24px，为增大尺度有意差 4px'),
]: lines.append(row(*args))
lines += ['', '## 移动设计目标（业主图优先，Preline 移动仅兜底）', '',
 '业主图是 736×1104 合成设计稿，没有 CSS/DOM；下列目标为从图中观察结构后采用的 390 布局尺度，不能声称是 getComputedStyle 的图稿测值。图稿裁切放大只用于并排观感，不作像素一致或字体测量证据。', '',
 '| 面 | 主参照映射 | 导航形态 | 瓦片列数 | 最小触控高 | 页面侧边距 | 底栏整高 |', '|---|---|---|---|---|---|---|']
checks = json.loads((P/'mobile-check.json').read_text()) if (P/'mobile-check.json').exists() else []
for name, ref in [('overview','Home: greeting + shortcuts'),('inquiries','My Courses: status rows'),('inquiry-detail','Fee Summary: amount + CTA'),('documents','Fee Summary: date + download'),('saved-solutions','My Courses: list/empty'),('company','My Profile: initials + full-width edit'),('account-details','My Profile: initials + full-width edit')]:
 rec = next((r for r in checks if r['name']==name and r['locale']=='en' and r['width']==390), {})
 lines.append(f'| {name} | {ref} | 四键 fixed + 七入口折叠菜单 | '+('四快捷入口 / 四态两列' if name=='overview' else '不适用')+f' | {rec.get("minTarget", "not run")}px（目标 ≥44） | {rec.get("gutter","not run")}px（目标16） | {rec.get("bottomHeight","not run")}px（64+1边框） |')
lines += ['', '移动补充：状态瓦片 173×116、两列 gap12；快捷瓦片 83.5×80、四列 gap8；标题24/32/600；输入48px；save CTA48px固定在底栏之上，间隔12px；无 CTA 页面底部预留100px，有 CTA 页面预留220px，均另加 safe-area。',
 '390/430 × EN/DE 的最后一个可交互元素 hit-test 与全菜单七入口证明见 mobile-check.json；未伪造空态中不存在的动作。',
 '颜色取 shared tokens；主参照的学生/课表/学费/进度不复制，既有四态数据与 PI 金额是唯一对应物。', '',
 '## 横向溢出', '', '| 本地截图组 | 通过 |','|---|---|']
for locale, file in [('EN','measurements-ours.json'),('DE','measurements-ours-de.json')]:
 data = json.loads((P/file).read_text())
 lines.append(f'| {locale} 7页 × 3视口 | {sum(r["overflow"]["viewport"]==r["overflow"]["document"] for r in data.values())}/{len(data)} |')
(P/'metrics.md').write_text('\n'.join(lines)+'\n')
print('Generated metrics.md from raw measurements and mobile behavior evidence')
