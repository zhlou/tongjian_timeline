# Known Issues

Remaining data-quality issues in `raw_json_converted/` as of 2026-07-11.
Items marked `[fixed]` are already corrected; unmarked items need attention.

---

## 1. Remaining moji-bake: `纟斥` (5 occurrences)

Both our text and the Wikisource epub have corruption here (`纟斥` / `丝斥`).

| Volume | Context | Probable correction |
|---|---|---|
| 258 | `存孝械揆及归范，纟斥以素练，徇于潞州城下` | `系`? (to bind) |
| 259 | `以练纟斥之，徇于城下` | `系`? |
| 262 | `复还，纟斥之以练，造可[壁下示之` | `系`? |
| 269 | `晋王以练纟斥刘仁恭父子，凯歌入于晋阳` | `系`? |
| 269 | (continuation of above) | |

Determining the correct character requires checking the standard Zhonghua Shuju edition.

---

## 2. Hex-fragment remnants (GBK code-point residues)

These are unlikely to be correctable by alignment (need a human to look up the GBK code).

| Volume | Text |
|---|---|
| 083 | `太子为[A170]求王爵` (3×) |
| 144 | `[B163]败走` (2×) |
| 213 | `谓君[B134]曰` (5×) |

---

## 3. Bracket-placeholder notation `{…}`

These are Wikisource editorial annotations representing partially legible or variant characters. Not corruption — they are intentional notation.

| Pattern | Count | Example context |
|---|---|---|
| `{艹}` | 2 | `日中必{艹}，操刀必割` (vols 014, 040) |
| `{土}` | 1 | `中{土}将军` (vol 112) |
| `{敝衣}` | 1 | `难可轻{敝衣}衣裾` (vol 138) |
| `{q弁}` | 2 | `令公主执{q弁}，行盥馈之礼` (vol 194) |
| `{麻女}` | 2 | `益怜阿{麻女}者` (vol 179) |
| `{衍食}` | 2 | `薄田足以具{衍食}粥` (vol 179) |
| `{父者}` | 2 | `前为皇后阿{父者}` (vol 210) |
| `{须巾}` | 2 | `军士首系白{须巾}为号` (vol 254) |
| `{鹿加}` | 2 | `神{鹿加}村` (vol 231) |
| `{山义}` | 10 | `袁{山义}为宣徽南院使` (vols 288-289) |
| `{q服}` | 2 | `嗣昭{q服}中矢尽` (vol 271) |
| Various others | ~30 | One-off notations throughout |

These are primarily in pairs — a `{` followed by a matching `}` — and represent a Wikisource convention for unclear characters. They are `correct_text.py`'s responsibility area (the script already detects `_RE_BRACKET_PLACEHOLDER`).

---

## 4. Angle-bracket compound characters `<…>`

These represent single rare characters that the digitizer notated as two CJK characters in angle brackets. Not corruption — notational convention.

| Pattern | Count | Context |
|---|---|---|
| `<妥页>` | 4 | `吕<妥页>之夫` (vol 012, family name) |
| `<黄有>` | 2 | `<黄有>领九真太守` (vol 066, name) |
| `<辶彖>` | 2 | `逵，<辶彖>之兄也` (vol 107) |
| `<扁瓜>` | 5 | `黄<扁瓜>少师` (vols 147, 213, title/name) |
| `<卵>` | 3 | `一子不<卵>` (vol 151, character component) |
| `<麦O>` | 2 | `课麦<麦O>迟晚` (vol 178) |
| `<矛赞>` | 4 | `超帅江淮排<矛赞>` (vols 181, 185, weapon name) |
| `<卤亢>` | 5 | `据豆子<卤亢>` (vols 181, 183, 184, place name) |
| `<风日>` | 2 | `谢<风日>王特勒` (vol 212, country name) |
| `<麦弋>` | 2 | `淘墙<麦弋>及马矢以食` (vol 221) |
| `<麦胡>` | 2 | `<麦胡>心存抚使` (vol 205, name) |
| `<丕页>` | 6 | `于<丕页>素善` (vol 235, name) |
| `<立义>` | 6 | `沈<立义>结女学士` (vol 245, name) |
| `<厂盍>` | 6 | `国人立<厂盍>特勒为可汗` (vol 246, name) |
| `<多周>` | 4 | `号<多周>金堡三王` (vol 269, place name) |

Unresolved — need a separate processing step or manual review.

---

## 5. Stray ASCII characters (single-character corruptions)

### 5a. `]` — corrupted name characters (~150 occurrences)

Most are the same GBK trail-byte corruption as `correct_text.py` handles, but the corresponding lead byte was lost so alignment can't determine the correct CJK character.

| Cluster | Volumes | Context |
|---|---|---|
| `梁[` | 049 | `诏以北地梁[为西域副校尉` (19× — personal name) |
| `雍]` | 070 | `雍]杀太守正昂` (7× — personal name 雍闿) |
| `柳]` | 199,200,208 | `中书令柳]以王皇后宠衰` (20× — personal name 柳奭) |
| `郎]` | 095,098,099 | `郎]为司空` (5× — personal name) |
| `罗希]` | 215 | `杭州人罗希]` (9× — personal name 罗希奭) |
| `张]` | 094,267,268,270,271,272,275,277 | `河南尹张宗]` (12× — personal name 张全义) |
| `李君]` | 249 | `醴泉令李君]` (4× — personal name) |
| `韩]` | (various) | Multiple individuals |
| Various | — | ~100 other one-off name characters |

### 5b. `[` — corrupted character (~200 occurrences, mixed causes)

| Cluster | Volumes | Context |
|---|---|---|
| `[欷` | 037,065,068,076,079,080,089,092,103,111,117,137,157,161,162,164,167,171,175,177,180,183,184,186,187,190,197,201,218,229,230,234,241,262,272 | `[欷流涕` → should be `歔欷` (to sob) — ~35 occurrences |
| `司马国[` | 114,115,116,117,118,119 | `司马国[及弟叔[` (18× — person name 司马国璠) |
| `浑{` | 217,223,224,225,227-237,240,263 | `浑{` → `浑瑊` (Tang general) — ~50 occurrences. `{` should be `瑊` |
| `李[` or `刘[` or `王[` | various | Various personal names |
| `可[` | 260,262 | `副使陈可[` (8× — personal name 陈可璠) |
| `陈[` | 254,289 | `刺史陈[` (4× — personal name) |

### 5c. `{` — corrupted character (matches cases from 5b + bracket-placeholder)

Many `{` occurrences are personal name characters (e.g. `李{` → `李鄘`), but the `{…}` bracket-placeholder notation described in §3 also uses this character. The two cases need to be distinguished.

### 5d. Other single-char ASCII remnants

| Char | Volumes | Context | Probable fix |
|---|---|---|---|
| `\` | 064,120 | `乃还\绖` / `吉痴蚰\` | Stray backslash, text cleanup |
| `_` | 224,258 | `杨_等` / `徐公_` | Stray, text cleanup |
| `|` | 161,204 | `侃子|` / `铁|入云` | Stray, text cleanup |
| `^` | 158 | `噤^良久` | Probably `噤齘良久` |
| `@` | 100,195,258 | `@鸡` / `火@` / `恭俟a@` | Various |
| `+` | 039,050,111 | `带++足恽` / `卢匆++心` | Multiple ASCII residue |
| `~` | 134 | `范~` | Personal name corruption |
| `` ` `` | 078,137,180,244 | `白蚺`` / `衣、蚺`` / `戴]` / `沈<立义>` | Mixed issues |
| `'` | multiple | `(various)` | Very rare |

---

## 6. Remaining radical+component splits

Patterns where a CJK radical (纟, 钅, 亻, 讠, 扌, 礻, 忄, etc.) appears as a standalone character followed by what should be its phonetic component. ~243 remaining, mostly in cases where the epub alignment couldn't confirm the correct character.

### High-frequency patterns

| Pattern | Approx. Count | Probable correction |
|---|---|---|
| `亻及` | 6 | `伋` (personal name) |
| `扌彖` | 6 | `掾` (official title, aide/supervisor) |
| `讠斤` | 8 | `訢` (personal name) |
| `忄官` | 5 | `悺` (personal name — already partially fixed) |
| `亻由` | 6 | `伷` (personal name — partially fixed) |
| `氵奏` | 8 | `湊` (personal/place name — partially fixed) |
| `礻氏` | 4 | `祇` (deity/spirit) |
| `辶彖` / `<辶彖>` | 1 | Noted in §4 |
| `阝善` | 5 | `鄯` (place name 鄯善) |
| `讠卓` | 8 | `焯` (personal name) |

### Lower-frequency patterns

| Pattern | Count | Volumes | Probable fix |
|---|---|---|---|
| `忄妻` | 3 | 031, 064 | `凄` (partially fixed) |
| `忄栗` | 4 | 044,103,157,278 | `慄` (to tremble) |
| `氵单` | 4 | 172,184,188,221 | `禪` (place name 中禪城) |
| `氵隐` | 2 | 076 | `隱` (place name 隱水) |
| `礻合` | 1 | 184 | `祫` (ritual) |
| `饣甫` | 1 | 038 | `哺` (partially fixed) |
| `氵具` | 3 | 021 | `具` (place name 具水) |
| `钅句` | 2 | 030 | `鉤` (place name — partially fixed) |
| `礻奏` | 1 | 048 | `祋` (personal name — partially fixed) |
| `亻叔` | 2 | 218,219 | `俶` (personal name — partially fixed) |
| `亻炎` | 1 | 218 | Some personal name character |

**~180 remaining one-off patterns** with the same radical-split structure but low frequency.

---

## 7. Expected: ruler-name promotion (not a bug)

`verify_counts.py` shows 41 files with 1–2 fewer year-sections in `semantic_json/` than the raw text count. This is expected behavior: `restructure_json.py`'s `_is_ruler_name()` detects standalone ruler-name paragraphs (e.g. `威烈王`, `昭烈帝`) and promotes them to `era_name` rather than leaving them as `main_text`.

- **41 files affected, 45 total promotions**
- **No data loss** — the ruler-name text becomes the era_name, not discarded

---

## 8. CJK-CJK edition variants (WON'T FIX)

`correct_text.py --review` reports ~57,300 CJK character mismatches between our simplified text and the Kanripo traditional reference after OpenCC `t2s` conversion. These are legitimate edition/form variants (e.g. `于`/`於`, `关`/`闗`, highly variant glyphs), not corruptions. No action required.

---

## Summary of actionable remaining items

| # | Item | Count | Action |
|---|---|---|---|
| 1 | `纟斥` → correct character | 5 | Research Zhonghua Shuju edition |
| 2 | Hex fragments `[A170]`, `[B134]`, `[B163]` | 10 | Look up GBK codes if recoverable |
| 3 | `{Bracket}` placeholders | ~60 | Could be resolved by consulting other editions |
| 4 | `<Angle>` compound chars | ~60 | Need a separate processing script or manual mapping |
| 5a | `]` — corrupted name chars | ~150 | Most need human lookup |
| 5b | `[` — corrupted chars | ~200 | Mixed (some `[欷→歔欷` is easy, others need lookup) |
| 5c | `{` — ambiguous: name_char vs. bracket-placeholder | ~100 | Needs classification first |
| 5d | Other stray ASCII (`\`, `_`, `|`, `^`, `@`, `+`) | ~20 | Most are simple text cleanup |
| 6 | Radical+component splits (remaining) | ~243 | Many have been partially fixed; remaining need confirmations |
