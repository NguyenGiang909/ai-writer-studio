# AI WRITER STUDIO --- MOCKUP PROJECT SPEC

## Demo Project: Vĩnh Thành

### Phiên bản: Mockup Seed v1.0

------------------------------------------------------------------------

# 1. MỤC ĐÍCH FILE

File này là đặc tả đầu vào để một AI thiết kế / AI coding agent tạo
mockup cho ứng dụng **AI Writer Studio**.

Không được hiểu đây chỉ là yêu cầu "làm một trang đọc truyện". Mockup
phải thể hiện một **workspace dành cho tác giả viết tiểu thuyết dài**,
trong đó AI hỗ trợ nhưng tác giả giữ quyền quyết định Canon.

Project demo dùng để kiểm thử ứng dụng là **Vĩnh Thành** --- một tiểu
thuyết huyền nghi đô thị, giả tưởng nhận thức và xã hội học. Project này
cố ý có nhiều lớp Canon, ký ức, phiên bản lịch sử, mystery và quan hệ
nhân vật để kiểm thử khả năng quản lý truyện dài của app.

## Mục tiêu UX

Tác giả có thể:

1.  Quản lý Project → Volume → Arc → Chapter → Scene.
2.  Viết khoảng 5--15 dòng Author Brief rồi yêu cầu AI mở rộng thành
    1.000--3.000 từ.
3.  Xem chính xác Context nào sẽ được gửi cho AI trước khi viết.
4.  Quản lý Canon, nhân vật, thế giới, quan hệ, timeline và mystery.
5.  Phân biệt "sự thật của thế giới" với "điều nhân vật tin/nhớ".
6.  Phát hiện continuity error và plot hole.
7.  Cho phép AI đề xuất nhưng không tự ý sửa Canon.
8.  Thử What-if mà không làm thay đổi truyện chính.
9.  Sau khi AI viết xong, tác giả duyệt các thay đổi trước khi chúng trở
    thành Canon.

------------------------------------------------------------------------

# 2. NGUYÊN TẮC SẢN PHẨM BẮT BUỘC

## 2.1 Author-first

AI là trợ lý sáng tác, không phải tác giả tự trị.

Luồng chính:

**Author Brief → Preview Plan → Preview Context → AI Expand → Review →
Approve/Reject → Canon Update**

AI không được tự động quyết định một mystery lớn, quan hệ quan trọng,
cái chết, năng lực, lịch sử hay world rule nếu tác giả chưa chấp thuận.

## 2.2 Canon là nguồn sự thật

Mọi dữ liệu cần có trạng thái rõ ràng:

-   `CANON`: tác giả đã xác nhận.
-   `PLANNED`: đã dự kiến nhưng chưa xuất hiện chính thức.
-   `HYPOTHESIS`: giả thuyết của nhân vật/hệ thống.
-   `VARIANT`: một phiên bản lịch sử hoặc What-if.
-   `UNKNOWN`: cố ý chưa xác định.
-   `REJECTED`: ý tưởng đã loại bỏ.

Không được biến `HYPOTHESIS` thành `CANON`.

## 2.3 Temporal Story State

App phải biết trạng thái truyện tại từng thời điểm/chương.

Ví dụ ở chương 5 Minh chưa biết An Vũ là ai thì AI viết chương 5 không
được sử dụng kiến thức Minh chỉ biết ở chương 17.

## 2.4 Knowledge ≠ Memory ≠ Reality

Đây là yêu cầu cốt lõi của mockup.

Ví dụ:

-   Current Reality: hồ sơ ghi Minh làm ở Cục Lưu trữ 6 năm.
-   Minh Memory: Minh nhớ mình làm 7 năm.
-   Minh Knowledge: Minh biết hai dữ liệu này mâu thuẫn.
-   Canon: chưa xác định phiên bản nào "nguyên bản".

App phải hiển thị và xử lý riêng bốn lớp này.

------------------------------------------------------------------------

# 3. PROJECT DEMO

## Tên

**Vĩnh Thành**

## Thể loại

-   Huyền nghi đô thị
-   Giả tưởng nhận thức
-   Speculative social fiction
-   Tâm lý
-   Linh dị phi thần quỷ
-   Mystery
-   Triết học

Không định hướng truyện thành ma quỷ, trừ tà, quái vật săn người hoặc
horror jump-scare.

## Logline

Một nhân viên lưu trữ phát hiện Vĩnh Thành liên tục tái cấu trúc sau
02:00. Không chỉ kiến trúc mà ký ức, quan hệ và lịch sử cũng thay đổi.
Trong quá trình tìm kiếm An Vũ --- người mà bằng chứng cho thấy anh từng
vô cùng thân thiết nhưng bản thân không còn nhớ --- Minh Trần dần phải
đối diện với câu hỏi liệu có tồn tại một phiên bản cố định của con người
và thế giới hay không.

## Quy mô dự kiến

-   80--150 chương.
-   Nhiều Volume.
-   Volume I: khoảng 30 chương.
-   POV chủ đạo: Minh Trần.
-   Không mở toàn bộ world ngay từ Volume I.

## Câu hỏi mystery bề mặt

**An Vũ là ai, chuyện gì đã xảy ra với cô và tại sao Minh từng hứa "Tôi
sẽ không quên"?**

## Câu hỏi xuyên suốt

**Nếu một con người, một mối quan hệ và cả quá khứ đều có thể thay đổi,
điều gì khiến chúng vẫn là "thật"?**

## Mạch phát triển sâu hơn

1.  Thành phố đang xảy ra chuyện gì?
2.  Phiên bản nào là thật?
3.  Làm sao con người biết một thứ là thật?
4.  Nếu ký ức không chắc chắn thì "tôi" là ai?
5.  Nếu bản ngã và quan hệ đều thay đổi, trách nhiệm và tình yêu dựa vào
    đâu?
6.  Có tồn tại một nền thực tại bất biến không?
7.  Nếu không có sự chắc chắn tuyệt đối, con người nên sống thế nào?

## Motif

**"Tôi sẽ không quên."**

Ý nghĩa thay đổi theo truyện:

-   Ban đầu: giữ đúng quá khứ.
-   Sau: chống lại sự tái cấu trúc.
-   Sâu hơn: không để một người bị xóa khỏi ý nghĩa của đời mình.
-   Cuối cùng: không quên không nhất thiết đồng nghĩa với nhớ chính xác.

------------------------------------------------------------------------

# 4. TRIẾT LÝ THẾ GIỚI

Vĩnh Thành không phải "thành phố ma".

Nó là một mô hình cô đặc của sự biến đổi vốn có trong đời sống.

Trong đời thường:

-   con người già đi;
-   thành phố đổi;
-   ký ức phai;
-   quan hệ thay đổi;
-   lịch sử được diễn giải lại.

Vĩnh Thành làm quá trình ấy diễn ra đủ nhanh để con người không thể duy
trì ảo giác rằng mọi thứ cố định.

Truyện có thể đối thoại với các vấn đề:

-   vô thường;
-   vô ngã;
-   duyên khởi;
-   giới hạn của ngôn ngữ;
-   chủ thể và khách thể;
-   ký ức;
-   nhận thức liên chủ thể;
-   bản sắc cá nhân;
-   quan hệ xã hội;
-   giá trị của bằng chứng;
-   khoa học và giới hạn đo lường.

Không tuyên bố một trường phái triết học hay tôn giáo là đáp án cuối
cùng.

Các câu hỏi triết học không phải plot hole cần "giải bằng lore".

------------------------------------------------------------------------

# 5. WORLD RULES --- CANON HIỆN TẠI

## 5.1 Tái cấu trúc

Sau khoảng 02:00, một số phần của Vĩnh Thành có thể xuất hiện sai lệch.

Không phải toàn thành phố cùng thay đổi và không phải đêm nào cũng giống
nhau.

Các cấp nội bộ để quản lý:

1.  Vật thể: cửa, phòng, đồ vật, biển số.
2.  Kiến trúc: tầng, tòa nhà, đường, ga.
3.  Xã hội: công việc, gia đình, công ty, quan hệ.
4.  Lịch sử: sự kiện quá khứ.
5.  Tồn tại: cá nhân hoặc cộng đồng từng tồn tại trở thành chưa từng tồn
    tại.

Không hiển thị hệ này cho độc giả như RPG level.

## 5.2 Không có mặc định "phiên bản cũ là thật"

Minh nhớ một khách sạn 8 tầng nhưng hiện tại mọi bằng chứng có thể cho
thấy nó luôn có 9 tầng.

Không được tự động kết luận ký ức Minh là "thực tại gốc".

## 5.3 Trọng lượng tồn tại

Đây hiện là **HYPOTHESIS mạnh**, chưa phải chân lý tối hậu.

Một sự tồn tại dường như càng được nhiều quan hệ xác nhận thì càng khó
bị tái cấu trúc.

Các lớp neo có thể gồm:

-   vật chất;
-   ký ức;
-   quan hệ;
-   hồ sơ;
-   pháp luật;
-   dữ liệu;
-   kinh tế;
-   văn hóa;
-   câu chuyện được truyền lại.

Hệ quả xã hội tiềm năng: những người ở rìa xã hội, ít quan hệ và ít hồ
sơ có thể dễ bị "làm mờ" hơn.

## 5.4 Neo

Một số vật/medium dường như giữ dấu vết lịch sử cũ tốt hơn:

-   chữ viết tay;
-   ảnh film;
-   băng analog;
-   vật thủ công;
-   một số tài liệu cũ;
-   vật gắn với quan hệ cá nhân mạnh.

Đây chưa phải quy luật tuyệt đối.

------------------------------------------------------------------------

# 6. NHÂN VẬT

## 6.1 Minh Trần

**Role:** Main Character / POV\
**Occupation:** Nhân viên Cục Lưu trữ Đô thị.

### Tính cách

-   Cẩn thận.
-   Thiên về kiểm chứng.
-   Có thói quen ghi chép.
-   Không dễ chấp nhận giải thích huyền bí.
-   Dần trở nên ám ảnh với việc xác định cái gì là thật.

### Arc nhận thức

Ban đầu: \> Có người sửa hồ sơ.

Sau: \> Thành phố đang thay đổi.

Sau nữa: \> Lịch sử đang thay đổi.

Sâu hơn: \> Quan hệ giữa các sự vật đang tái cấu trúc.

Cuối đường: \> Có thể chính nhu cầu tìm một phiên bản tuyệt đối mới là
điều cần xem xét.

### Khả năng hiện tại

Minh có thể giữ lại một số ký ức không hoàn toàn đồng bộ với hiện thực
mới.

Framework nội bộ ban đầu: khoảng ba sai lệch lớn qua một chu kỳ, nhưng
không được trình bày như "3 slot năng lực".

Cố giữ quá nhiều ký ức về sai lệch có thể đi kèm việc những ký ức cá
nhân khác mờ đi.

Chưa khóa nguyên nhân.

Status của nguyên nhân: `UNKNOWN`.

------------------------------------------------------------------------

## 6.2 An Vũ

**Role:** Core Mystery / Relationship Axis.

### Canon tối thiểu

-   Có bằng chứng An từng liên hệ sâu với Minh trong ít nhất một phiên
    bản lịch sử.
-   Hồ sơ hiện tại không khớp với quá khứ Minh tìm thấy.
-   Kiến thức của An có giới hạn.
-   Không được biến An thành NPC biết toàn bộ lore.

### Current Reality

Có khả năng tồn tại một An Vũ đang sống tại Vĩnh Thành với lịch sử hoàn
chỉnh không có Minh.

### Historical Variants

-   Variant A: đồng nghiệp.
-   Variant B: quan hệ thân mật/tình cảm.
-   Variant C: gặp nhau sau Sự kiện Mất Điện.
-   Các variant chưa được ưu tiên thành Canon tối hậu.

### Hành vi quan trọng

An từng tạo nhiều liên hệ xã hội nhỏ:

-   vay tiền;
-   gửi sách;
-   mua bán;
-   đăng ký hội viên;
-   viết thư;
-   xuất hiện trong ảnh;
-   làm quen người bán hàng.

Planned Reveal: An không đơn giản để lại clue. Cô đang cố phân tán bằng
chứng về sự tồn tại của mình vào mạng lưới xã hội.

------------------------------------------------------------------------

## 6.3 Bà Lệ

**Role:** Recurring / Witness / Philosophical Counterpoint.\
**Occupation:** Chủ khách sạn.

### Canon

-   Có tính liên tục ký ức cao.
-   Đã chứng kiến nhiều phiên bản của khách sạn.
-   Biết nhiều hơn Minh nhưng không biết tất cả.
-   Reliability: `UNCERTAIN`.

### Thái độ

Minh cố tìm phiên bản thật.

Bà Lệ đã sống đủ lâu để không còn tin rằng mọi thứ phải có một phiên bản
bất biến.

Bà không đại diện cho "chân lý của tác giả".

------------------------------------------------------------------------

## 6.4 Hạ --- tên tạm

**Role:** Relationship / Daily Life / Intimacy.

Không phải "cô gái chữa lành".

Hạ có đời sống riêng và sự cô độc riêng.

Quan hệ với Minh từng thân mật nhưng không khóa ngay thành "tình yêu
lớn".

Hạ giúp truyện khảo sát:

-   thân mật thể xác;
-   ký ức cơ thể;
-   sự cô độc;
-   khoảng cách giữa hai người;
-   một quan hệ có thể tồn tại dù lịch sử của nó không còn rõ.

Cảnh thân mật có thể trưởng thành nhưng không dung tục; trọng tâm là tâm
lý, khoảng cách và nhận thức.

------------------------------------------------------------------------

# 7. ĐỊA ĐIỂM

## 7.1 Khách sạn 9 tầng

**Current Reality:** 9 tầng.\
**Historical Evidence:** từng có dấu vết 7 tầng và 8 tầng.\
**Owner:** Bà Lệ.

Không có hồ sơ xây thêm tầng hoàn chỉnh.

Kích thước bên trong có thể lớn hơn kích thước đo từ bên ngoài.

### Tầng 9

Không phải "tầng ma".

Có mức bất ổn nhận thức cao.

Ví dụ:

-   lễ tân nhớ 12 phòng;
-   nhân viên dọn phòng nhớ 14;
-   camera cho thấy 8 cửa.

Các bằng chứng có thể đồng thời hợp lệ.

### Hành lang Đông

Nằm tại tầng 3.

Sau 02:00 đôi khi xuất hiện một đoạn hành lang/cửa/phòng không có trong
sơ đồ hiện tại.

------------------------------------------------------------------------

## 7.2 Ga tàu Đông Thành

**Status:** Đóng cửa từ Sự kiện Mất Điện.

**Current Structure:** 4 lối hầm.

**Historical Evidence:** có bản vẽ chỉ có 3.

**Hầm số 4:** vẫn có hoạt động sau 02:00.

Một số chuyến tàu có thể thuộc mạng lưới/lịch sử Vĩnh Thành khác.

Không gọi chúng là tàu ma.

### ET-04

Một chuyến tàu liên quan Sự kiện Mất Điện và An Vũ.

Mystery status: `OPEN`.

------------------------------------------------------------------------

# 8. 9 VÙNG VĨNH THÀNH

Không cần mở hết trong Volume I.

Mỗi vùng đại diện cho một vấn đề xã hội/nhận thức, không phải một "map
kinh dị".

## 1. Trung tâm Cũ

**Question:** Ai quyết định quá khứ?

Có Cục Lưu trữ, tòa án, thư viện, khách sạn.

## 2. Đông Thành

**Question:** Một đời người có thể đã đi theo con đường khác không?

Ga tàu, khu trọ, lao động, người nhập cư.

## 3. Bắc Cảng

**Question:** Giá trị của một thứ đến từ đâu?

Có thị trường "Đồ Lệch": vật thể thuộc lịch sử không còn tồn tại.

## 4. Nam Minh

**Question:** Gia đình là ký ức hay quan hệ?

Chung cư, trường học, gia đình, hôn nhân.

## 5. Tây Viên

**Question:** Nếu khoa học đo được hai sự thật thì sao?

Đại học, bệnh viện, thần kinh học, vật lý, thống kê, data center.

## 6. Khu 17

**Question:** Một cộng đồng có tồn tại nếu không ai nhớ nó?

Dấu vết một khu dân cư hàng chục nghìn người không còn trong lịch sử
hiện tại.

## 7. Hạ Giang

**Question:** Truyền khẩu có kém thật hơn tài liệu không?

Làng cổ, gia phả, tên đất, bài đồng dao, truyền thống.

## 8. Tân Hải

**Question:** Con người là bản thân họ hay dữ liệu về họ?

Tài chính, công nghệ, AI, danh tính số.

## 9. Vành đai Trắng

**Question:** Thành phố kết thúc ở đâu?

Ranh giới, thuộc về, trung tâm/ngoại vi.

------------------------------------------------------------------------

# 9. MYSTERY TRACKER MẪU

## M-001 --- An Vũ là ai?

Status: `OPEN`\
Introduced: Ch.2\
Priority: Critical

Evidence: - chữ ký An; - chìa khóa; - ảnh Minh--An; - thư; - giao dịch
xã hội; - vé ET-04.

Planned Reveal: An từng cố tạo nhiều neo xã hội để bảo vệ tính liên tục
của mình.

Target: khoảng Ch.27.

Closure: `PARTIAL`.

## M-002 --- Vì sao khách sạn có 9 tầng?

Status: `OPEN`.

AI Rule: Không tự giải thích nguồn gốc cuối cùng.

## M-003 --- Hầm số 4

Status: `OPEN`.

Known: - hiện tại tồn tại; - tài liệu cũ có lúc không tồn tại; - hoạt
động sau 02:00; - liên hệ ET-04.

## M-004 --- Sự kiện Mất Điện

Status: `OPEN`.

Có nhiều tài liệu hợp lệ nhưng mâu thuẫn về thời lượng và diễn biến.

## M-005 --- Vì sao Minh giữ được ký ức?

Status: `OPEN`.

Không được tự giải bằng "Minh được chọn", huyết thống bí mật hoặc thần
lực nếu tác giả chưa duyệt.

## Q-001 --- Có thực tại nguyên bản không?

Type: `PHILOSOPHICAL QUESTION`\
Status: `INTENTIONALLY UNRESOLVED`.

Không được đánh dấu là plot hole.

## Q-002 --- Cái tôi là gì khi ký ức thay đổi?

Type: `PHILOSOPHICAL QUESTION`.

Được khảo sát qua hành động và quan hệ, không giải bằng lore dump.

------------------------------------------------------------------------

# 10. NGUYÊN TẮC QUẢN LÝ MYSTERY

Mỗi mystery nên có:

-   Question.
-   Introduced At.
-   Evidence.
-   False Leads nếu có.
-   Character Knowledge.
-   Planned Reveal.
-   Target Chapter/Arc.
-   Closure Level.
-   Dependencies.
-   Canon Impact.

Quy tắc dài hạn:

**Mỗi khoảng 10 chương phải có ít nhất một mystery được giải thật.**

Không được chỉ liên tục biến câu hỏi nhỏ thành câu hỏi lớn hơn.

Nguyên tắc arc:

**Mở 1 hố lớn → giải 1 hố cũ → làm sâu 1 câu hỏi chủ đề.**

Triết học không được dùng để che plot hole.

------------------------------------------------------------------------

# 11. VOLUME I --- NGƯỜI KHÔNG CÓ TRONG HỒ SƠ

Khoảng 30 chương.

## Arc 1 --- Bản đồ có chín tầng

### Ch.1 --- Hồ sơ không khớp

Minh phát hiện bản vẽ khách sạn 8 tầng trong khi hồ sơ hiện tại ghi 9.
Sau khi hỏi đồng nghiệp, bản vẽ dường như cũng trở thành 9 tầng. Chỉ ghi
chú tay "8T" của Minh còn khác.

### Ch.2 --- Một cái tên thừa

Minh thấy chữ ký An Vũ trong hồ sơ nhưng hệ thống nhân sự không có người
này. Bên cạnh là nét chữ của chính Minh.

### Ch.3 --- Người đồng nghiệp không tồn tại

Không ai nhớ An. Minh tìm được chìa khóa có ký hiệu A.V / 903.

### Ch.4 --- Khách sạn

Minh đến khách sạn. Bà Lệ nói "Lâu hơn lần trước" dù Minh tin đây là lần
đầu.

### Ch.5 --- Chín tầng

Minh đo khách sạn và phát hiện kích thước bên trong/bên ngoài không
khớp.

### Ch.6 --- Tôi sẽ không quên

Trong phòng 903, Minh tìm được ghi chú của An và câu "Tôi sẽ không quên"
bằng chữ của chính mình.

## Arc 2 --- Sau hai giờ

### Ch.7 --- Thử nghiệm đầu tiên

Minh chủ động đo và ghi chép khách sạn qua 02:00. Hành lang tầng 3 thay
đổi chiều dài.

### Ch.8 --- Hành lang Đông

Xuất hiện cửa thứ tám. Bên trong có ảnh Minh và An.

### Ch.9 --- Hạ

Chương đời sống/quan hệ. Minh gặp lại Hạ sau thời gian xa cách. Hai
người ăn khuya, uống rượu và gần gũi. Sáng hôm sau Minh nhận ra mình nhớ
sự thân thuộc nhưng không nhớ rõ lịch sử tạo nên nó. Không thêm clue An.

### Ch.10 --- Ba thứ

Minh nhận thấy mình giữ được một số sai lệch nhưng đồng thời mất một ký
ức cá nhân nhỏ.

### Ch.11 --- Bà Lệ

Bà Lệ cảnh báo: "Không phải cái gì cũng đáng mang sang ngày mai."

### Ch.12 --- Người khách 907

Một khách khẳng định ở đây 11 năm; lễ tân nói ba ngày. Sáng hôm sau
phòng 907 không còn trong cấu trúc hiện tại.

## Arc 3 --- An Vũ / đời sống

### Ch.13 --- Điều tra chính mình

Minh phát hiện hồ sơ về chính mình cũng mâu thuẫn.

### Ch.14 --- Đám tang

Một đồng nghiệp lớn tuổi chết vì nguyên nhân hoàn toàn bình thường.
Những người dự tang kể những phiên bản khác nhau về ông. Minh nhận ra
ngay cả không có Vĩnh Thành, một con người vẫn tồn tại khác nhau trong
ký ức người khác.

### Ch.15 --- Những khoản tiền nhỏ

Minh phát hiện hành vi xã hội kỳ lạ của An: vay tiền, gửi sách, mua bán,
đăng ký.

### Ch.16 --- Người nhớ An

Một người bán đồ ăn vẫn nhớ An qua chi tiết nhỏ: cô không ăn hành. Thiết
chế quên An nhưng một quan hệ đời thường vẫn giữ dấu vết.

### Ch.17 --- Đừng nhớ một mình

Minh tìm được trao đổi cũ giữa hai người. An từng viết: "Vậy đừng nhớ
một mình."

### Ch.18 --- Một mình

Chương không đặt nặng mystery. Minh đi qua Vĩnh Thành, nhìn hàng triệu
đời sống bình thường, cảm nhận sự cô độc giữa đô thị đông người.

### Ch.19 --- Một An khác

Minh tìm thấy An đang sống với một lịch sử hoàn chỉnh không có mình.

### Ch.20 --- Điều tàn nhẫn hơn mất tích

Minh đưa bằng chứng cho An. Ảnh giấy và dữ liệu số cho hai phiên bản
khác nhau. An yêu cầu Minh không can thiệp vào đời sống của cô.

## Arc 4 --- Đông Thành

### Ch.21 --- Tấm vé

Minh tìm được vé ET-04 liên quan An.

### Ch.22 --- Sự kiện Mất Điện

Ba nguồn hợp lệ mô tả ba lịch sử khác nhau.

### Ch.23 --- Hầm số 4

Minh xuống Hầm 4 sau 02:00.

### Ch.24 --- Nhà ga vẫn hoạt động

Ga ngầm hoạt động bình thường nhưng biển quảng cáo và tuyến tàu thuộc
một Vĩnh Thành khác.

### Ch.25 --- ET-04

Một đoàn tàu tới. Hành khách là người bình thường. Một phụ nữ xuống tàu
và nói Đông Thành của cô không có ga ngầm.

### Ch.26 --- Không lên tàu

Minh thấy người giống An trên ET-04 nhưng dừng lại vì lời cảnh báo. Khi
tàu rời đi, một nhân viên ga hành xử như ga chưa từng đóng.

## Arc 5 --- Người ta tồn tại như thế nào?

### Ch.27 --- Một Đông Thành khác

Minh trở về và thấy vài chi tiết đời mình đã lệch.

### Ch.28 --- An không để lại manh mối

Minh nhận ra các hành vi xã hội của An là cách phân tán bằng chứng về sự
tồn tại. Đây là reveal thật, không chỉ mở hố mới.

### Ch.29 --- Lời hứa

Bà Lệ trao một cuốn sổ Minh từng gửi bà. Trang đầu ghi "Gửi Minh tiếp
theo."

### Ch.30 --- Minh tiếp theo

Các phiên bản ghi chép của Minh không thống nhất: có bản gọi An là đồng
nghiệp, có bản là người yêu, có bản cảnh báo không được tin An. Dòng
cuối của An: "Lần tới, thử hỏi xem điều gì khiến chúng ta vẫn gặp lại
nhau."

------------------------------------------------------------------------

# 12. ĐỜI SỐNG VÀ TÌNH CẢM

Truyện không được trở thành chuỗi:

**phát hiện → clue → điều tra → reveal**.

Cần có đời sống không trực tiếp phục vụ mystery.

Các dạng scene:

-   ăn một mình;
-   đi làm;
-   thăm mẹ;
-   đám tang;
-   uống rượu;
-   gặp người cũ;
-   tình dục và thân mật;
-   tranh cãi;
-   đi bộ đêm;
-   sinh nhật;
-   cưới hỏi;
-   bệnh viện;
-   bạn bè dần xa;
-   những cuộc trò chuyện không cho Minh đáp án.

## Minh -- An

Là quan hệ trung tâm nhưng không khóa ngay thành romance.

Câu hỏi: **Tôi có nghĩa vụ với tình cảm của một phiên bản tôi mà tôi
không còn nhớ không?**

Nếu An hiện tại không nhớ Minh, Minh không có quyền ép cô tiếp tục một
quan hệ chỉ vì "quá khứ nói vậy".

## Minh -- Hạ

Một quan hệ đời thường, thân mật, không nhất thiết định danh rõ.

Dùng để khảo sát:

-   cơ thể và ký ức;
-   cô độc;
-   nhu cầu được chạm vào một người khác;
-   thân mật không đồng nghĩa với hiểu nhau;
-   lịch sử quan hệ có thể không đồng nhất.

## Minh -- gia đình

Một neo cảm xúc khác.

Có thể xuất hiện những ký ức gia đình không khớp.

Một câu tinh thần có thể dùng: "Nếu một ngày mẹ không nhớ con thì con
giới thiệu lại từ đầu."

Không bắt buộc dùng nguyên văn trong truyện.

## Minh -- Bà Lệ

Quan hệ giữa người cố giữ và người đã học cách sống cùng biến đổi.

Không phải sư phụ truyền lore.

## Minh -- chính mình

Minh có thể để lại thư, nhật ký và hướng dẫn cho "Minh sau".

Câu hỏi: **Tôi có nghĩa vụ phải trung thành với con người mà tôi từng là
không?**

------------------------------------------------------------------------

# 13. STORY TONE

-   Trưởng thành.
-   Tiết chế.
-   Cô độc nhưng không bi lụy liên tục.
-   Thành phố đông người nhưng con người có khoảng cách.
-   Mystery hiện diện dưới đời sống thường nhật.
-   Dị thường càng bình thường càng hiệu quả.
-   Không lạm dụng tiếng động kỳ quái, bóng đen, máu, quái vật.
-   Có sensuality và tình dục người lớn khi cần, nhưng không biến thành
    erotic fiction.
-   Triết học đi qua tình huống và lựa chọn, không phải nhân vật liên
    tục giảng đạo.

Không mô phỏng trực tiếp văn phong của một tác giả sống/cụ thể. Có thể
dùng các đặc tính cấp cao như: cô độc đô thị, tiết chế, đời sống thường
nhật xen bất định, khoảng trống trong quan hệ.

------------------------------------------------------------------------

# 14. MOCKUP --- INFORMATION ARCHITECTURE

Ưu tiên mobile/iPad. Không thiết kế desktop-first.

## Navigation chính

1.  Home / Projects
2.  Write
3.  Story
4.  World
5.  Characters
6.  Threads
7.  Timeline
8.  AI
9.  Settings

Trên mobile dùng bottom navigation + contextual drawer/sheet.

Trên iPad có thể dùng sidebar.

------------------------------------------------------------------------

# 15. PROJECT DASHBOARD

Project card:

**Vĩnh Thành**\
Huyền nghi đô thị · Giả tưởng nhận thức\
Volume I · 30 chapters planned\
Current: Ch.1 Draft\
\~0 / 90,000 words

Dashboard widgets:

-   Continue Writing.
-   Current Chapter.
-   Open Mysteries.
-   Continuity Warnings.
-   Character States.
-   Recent Canon Changes.
-   AI Credits / API status.
-   Project Progress.
-   Timeline snapshot.

------------------------------------------------------------------------

# 16. CHAPTER TREE

Hierarchy:

**Volume → Arc → Chapter → Scene**

Yêu cầu:

-   collapse/expand;
-   drag & drop;
-   status;
-   POV;
-   word count;
-   scene type;
-   target length;
-   continuity warning indicator.

Ví dụ:

Volume I --- Người không có trong hồ sơ - Arc 1 --- Bản đồ có chín
tầng - Ch.1 Hồ sơ không khớp - Scene 1: Cục Lưu trữ - Scene 2: Bản vẽ -
Ch.2 Một cái tên thừa - Arc 2 --- Sau hai giờ ...

Statuses: `Outline / Brief / Draft / Review / Canon / Rewrite`

Scene Types:
`Mystery / Discovery / Relationship / Intimacy / Daily Life / Reflection / Conflict / Transition / Reveal`

------------------------------------------------------------------------

# 17. WRITE SCREEN

Màn hình quan trọng nhất.

## Mobile

Top: - Back. - Chapter title. - Status. - More.

Body: - Editor.

Bottom/toolbar: - AI. - Context. - Notes. - Continuity.

AI mở dưới dạng bottom sheet.

## iPad

Có thể dùng 3 vùng:

-   Chapter Tree.
-   Editor.
-   AI/Context inspector.

Nhưng phải cho phép ẩn panel để tập trung viết.

------------------------------------------------------------------------

# 18. AUTHOR BRIEF

Fields:

-   Chapter goal.
-   5--15 dòng xương chương.
-   Target words.
-   POV.
-   Scene type.
-   AI Freedom.
-   Style/Tone.
-   Must Include.
-   Must Avoid.
-   Mystery permissions.
-   Relationship permissions.
-   Ending beat.

Ví dụ preset cho Ch.9 --- Hạ:

**Goal:** cho thấy đời sống thân mật của Minh và sự bất ổn của ký ức cá
nhân.

**Brief:** Minh nhận điện thoại của Hạ sau nhiều tháng. Hai người ăn
khuya. Quan hệ cũ không giải thích trực tiếp. Hạ chủ động rủ Minh ở lại.
Có thân mật nam nữ nhưng trọng tâm là khoảng cách giữa hai người. Sau đó
Minh nhận ra mình nhớ cảm giác thân thuộc nhưng không nhớ lần đầu họ gần
nhau. Hạ kể một kỷ niệm ba năm trước mà Minh hoàn toàn không nhớ. Không
xác nhận đây là tác động Vĩnh Thành. Không xuất hiện clue mới về An. Kết
bằng cảm giác hai người nằm rất gần nhưng lịch sử giữa họ trở nên xa.

**Target:** 2,000 words\
**POV:** Minh\
**AI Freedom:** Medium\
**Scene:** Relationship / Intimacy

------------------------------------------------------------------------

# 19. PREVIEW PLAN

Trước khi Expand, AI đề xuất kế hoạch ngắn:

1.  Opening beat.
2.  Scene progression.
3.  Emotional movement.
4.  Canon references to use.
5.  New facts AI muốn đề xuất.
6.  Ending beat.

Tác giả có thể:

-   Approve.
-   Edit.
-   Regenerate.
-   Reject individual proposed facts.

------------------------------------------------------------------------

# 20. PREVIEW CONTEXT

Phải hiển thị chính xác Context Builder sẽ gửi gì.

Ví dụ Ch.9:

### Included

-   Minh character card at Ch.9.
-   Hạ relationship card.
-   Current Vĩnh Thành rules known to Minh.
-   Ch.8 summary.
-   Current emotional state.
-   Style guide.
-   Relevant Canon.

### Excluded

-   Planned Ch.17 reveal.
-   Ch.27 reveal about An's social anchors.
-   Final theory of existence.
-   Future An variants.

Đây là tính năng quan trọng để tránh AI spoiler chính tác giả.

------------------------------------------------------------------------

# 21. AFTER-WRITE REVIEW

Sau khi AI Expand, app không cập nhật Canon ngay.

Hiển thị:

### Proposed Canon Changes

-   Minh và Hạ từng thân mật trước đây.
-   Hạ nhớ một sự kiện ba năm trước.
-   Minh không nhớ sự kiện đó.

Actions: `Approve / Reject / Edit`

### Continuity Warnings

Ví dụ: \> Warning: AI viết "Minh và Hạ yêu nhau bốn năm". Canon chưa xác
nhận thời lượng quan hệ.

> Warning: AI cho Minh biết ET-04 ở Ch.9. ET-04 chỉ được phát hiện ở
> Ch.21.

> Warning: AI khẳng định ký ức cơ thể chống tái cấu trúc. Đây chưa phải
> Canon.

### New Mystery Suggestions

Không tự tạo. Chỉ đề xuất và chờ duyệt.

------------------------------------------------------------------------

# 22. CHARACTER SCREEN

Mỗi character card có tabs:

-   Overview.
-   State.
-   Knowledge.
-   Memory.
-   Relationships.
-   Timeline.
-   Secrets.
-   Appearances.
-   Variants.

Ví dụ Minh tại Ch.10:

**Reality** Hồ sơ: 6 năm làm việc.

**Memory** Nhớ: 7 năm.

**Knowledge** Biết hồ sơ và ký ức mâu thuẫn.

**Belief** Nghi hồ sơ bị sửa.

**Canon Truth** Unknown.

------------------------------------------------------------------------

# 23. RELATIONSHIP SYSTEM

Quan hệ phải temporal.

Không chỉ:

`Minh → An = Love`.

Mà:

-   At Ch.1: Unknown.
-   Historical Variant A: Colleague.
-   Variant B: Intimate.
-   Ch.17 Current An → Minh: Stranger.
-   Minh → An: Curiosity / obligation / growing attachment.

Fields:

-   Person A.
-   Person B.
-   Current relationship.
-   Emotional direction.
-   Trust.
-   Known history.
-   Hidden history.
-   Variant histories.
-   Change log.

------------------------------------------------------------------------

# 24. WORLD SCREEN

Categories:

-   Locations.
-   Rules.
-   Factions.
-   Historical Events.
-   Artifacts/Anchors.
-   Culture.
-   Institutions.
-   Mysteries.
-   Hypotheses.

Map không bắt buộc ở mockup đầu.

Cards cần status badge:
`Canon / Planned / Hypothesis / Variant / Unknown`.

------------------------------------------------------------------------

# 25. THREADS / MYSTERY SCREEN

Hai loại thread phải khác nhau:

## Plot Mystery

Có expectation closure.

Ví dụ An Vũ, ET-04, Sự kiện Mất Điện.

## Philosophical Question

Không bắt buộc closure.

Ví dụ "Có thực tại nguyên bản không?"

UI không được đánh philosophical question thành overdue plot hole.

Hiển thị:

-   Open.
-   Progress.
-   Evidence.
-   Next planned beat.
-   Target reveal.
-   Closure.
-   Related chapters.
-   Related characters.

------------------------------------------------------------------------

# 26. TIMELINE

Cần hỗ trợ nhiều lớp:

1.  Narrative timeline.
2.  Current Reality timeline.
3.  Historical Variant timeline.
4.  Character remembered timeline.

Ví dụ cùng ngày có thể có:

`Reality A: Minh đi làm.`\
`Minh Memory: Minh nghỉ phép.`

UI nên cho bật/tắt layers.

------------------------------------------------------------------------

# 27. CONTINUITY ENGINE MOCKUP

Các warning mẫu:

### Knowledge leak

"Minh đang dùng thông tin chỉ An biết."

### Future spoiler

"Chi tiết này chỉ được reveal ở Ch.27."

### Canon conflict

"Khách sạn hiện tại đã khóa 9 tầng, đoạn văn viết 8 tầng mà không đánh
dấu historical variant."

### Relationship conflict

"An hiện tại chưa nhớ Minh."

### Mystery premature closure

"AI vừa xác nhận nguồn gốc Hầm 4 dù mystery đang OPEN."

### Temporal conflict

"Nhân vật sử dụng vật chưa nhận được ở thời điểm này."

### Philosophy vs Canon

"Câu 'không tồn tại thực tại gốc' đang được viết như fact. Hiện đây chỉ
là philosophical hypothesis."

------------------------------------------------------------------------

# 28. WHAT-IF SANDBOX

Tác giả có thể thử:

-   Nếu An nhớ Minh ở Ch.17?
-   Nếu Minh lên ET-04?
-   Nếu Hạ phát hiện nhật ký?
-   Nếu Bà Lệ nói thật sớm hơn?

What-if:

-   không thay Canon;
-   có branch riêng;
-   có thể compare impact;
-   chỉ merge khi tác giả xác nhận.

------------------------------------------------------------------------

# 29. AI DISCUSSION

Một chat riêng theo project.

AI có quyền đọc context được phép nhưng phải phân biệt:

-   fact;
-   author decision;
-   hypothesis;
-   suggestion.

Ví dụ tác giả hỏi:

> Nếu cho An và Minh từng là người yêu thì ảnh hưởng gì?

AI trả impact analysis nhưng không tự đổi relationship thành Canon.

Có nút:

`Promote to Planned` `Promote to Canon` `Save as What-if` `Discard`

------------------------------------------------------------------------

# 30. ACCOUNT / SETTINGS MOCKUP

Cần có:

-   Profile.
-   Credit/usage.
-   API provider.
-   API key input.
-   Model selection.
-   Context budget.
-   Default Expand length.
-   Data/export.
-   Theme.

API key UI chỉ là mockup, không hard-code secret.

------------------------------------------------------------------------

# 31. LIGHT / DARK DESIGN

Ứng dụng chủ yếu mobile/iPad.

## Light

-   Sáng, sạch, trung tính.
-   Không nền vàng kiểu parchment.
-   Editor có cảm giác giấy hiện đại nhưng trắng/xám rất nhẹ.
-   Tương phản đọc dài tốt.

## Dark

Không chỉ đổi background.

Cần hệ màu dark thực sự:

-   nhiều cấp surface;
-   border;
-   elevated sheet;
-   editor surface;
-   muted text;
-   semantic badge;
-   selected state;
-   input state.

Cảm giác: xám tối, yên, đọc truyện lâu được.

Không dùng pure black toàn màn hình nếu làm chữ quá gắt.

## Typography

Editor ưu tiên font có cảm giác viết/đọc văn chương nhưng vẫn dễ đọc.

UI dùng sans-serif sạch.

Mockup có thể cho tác giả chọn Editor Font.

------------------------------------------------------------------------

# 32. MOBILE UX

Mục tiêu iPhone:

-   một nhiệm vụ chính trên một màn hình;
-   panel phụ dùng sheet/drawer;
-   chapter tree có full-screen view;
-   AI chat/expand dùng bottom sheet;
-   Context Preview mở riêng;
-   không cố nhét desktop 3-column xuống màn hình nhỏ.

iPad: - hỗ trợ sidebar + editor + inspector; - panel collapsible.

------------------------------------------------------------------------

# 33. MOCK DATA CẦN HIỂN THỊ

Project: Vĩnh Thành.

Volume: Người không có trong hồ sơ.

Characters: - Minh Trần. - An Vũ. - Bà Lệ. - Hạ.

Locations: - Cục Lưu trữ. - Khách sạn 9 tầng. - Hành lang Đông. - Ga
Đông Thành. - Hầm số 4. - 9 vùng Vĩnh Thành.

Mysteries: - M-001 An Vũ. - M-002 tầng 9. - M-003 Hầm 4. - M-004 Sự kiện
Mất Điện. - M-005 ký ức Minh. - Q-001 thực tại nguyên bản. - Q-002 bản
ngã.

At least: - 30 chapter outline records. - 6--10 scene records. - 5
continuity warnings. - 3 proposed Canon changes. - 2 What-if branches.

------------------------------------------------------------------------

# 34. MOCKUP SCREENS CẦN TẠO

Ưu tiên các màn hình sau:

1.  Projects.
2.  Vĩnh Thành Dashboard.
3.  Chapter Tree.
4.  Write / Editor.
5.  Author Brief.
6.  Preview Plan.
7.  Preview Context.
8.  AI Expand / generation state.
9.  After-write Review.
10. Character Detail --- Minh.
11. Character Detail --- An.
12. Relationship --- Minh/An.
13. World.
14. Location Detail --- Khách sạn.
15. Mystery Tracker.
16. Mystery Detail --- An Vũ.
17. Timeline multi-layer.
18. Continuity Center.
19. AI Discussion.
20. What-if Sandbox.
21. Account / API / Credit.
22. Light Mode.
23. Dark Mode.

Không cần làm tất cả thành backend thật trong mockup, nhưng navigation
và state mẫu phải đủ để người dùng hiểu workflow.

------------------------------------------------------------------------

# 35. DEMO FLOW QUAN TRỌNG NHẤT

Mockup phải cho demo được flow sau:

1.  Mở Project Vĩnh Thành.
2.  Chọn Volume I.
3.  Chọn Ch.9 --- Hạ.
4.  Xem Author Brief.
5.  Nhấn Preview Plan.
6.  AI đưa scene plan.
7.  Nhấn Preview Context.
8.  Thấy AI được phép biết gì và bị chặn gì.
9.  Expand.
10. Hiển thị draft mẫu.
11. Continuity Engine bắt lỗi "Minh và Hạ yêu nhau 4 năm" vì chưa Canon.
12. AI đề xuất ba Canon changes.
13. Tác giả approve hai, reject một.
14. Story State được cập nhật.
15. Mystery Tracker không bị AI tự thêm lời giải.
16. Quay lại editor.

Flow này là heart of product.

------------------------------------------------------------------------

# 36. DỮ LIỆU / DOMAIN MODEL GỢI Ý

Không bắt buộc đúng schema backend, nhưng mockup/code nên phản ánh các
entity:

``` text
Project
Volume
Arc
Chapter
Scene
AuthorBrief
Draft
Character
CharacterState
CharacterKnowledge
CharacterMemory
Relationship
Location
WorldRule
HistoricalEvent
Artifact
Mystery
PhilosophicalQuestion
Evidence
TimelineEvent
HistoricalVariant
CanonFact
Hypothesis
ContinuityIssue
AIProposal
WhatIfBranch
StyleGuide
ContextBundle
```

Mỗi record quan trọng nên có:

``` text
id
projectId
status
validFrom
validUntil
sourceChapter
canonLevel
createdBy
updatedAt
```

Các entity temporal cần snapshot/version.

------------------------------------------------------------------------

# 37. AI CONTEXT BUILDER --- MOCK LOGIC

Khi viết một scene, Context Builder ưu tiên:

1.  Author Brief.
2.  Current Chapter/Scene state.
3.  POV Character State tại thời điểm scene.
4.  Characters xuất hiện trong scene.
5.  Relationship states.
6.  Relevant location.
7.  Active world rules.
8.  Open threads liên quan trực tiếp.
9.  Recent chapter summaries.
10. Style guide.

Không dump toàn bộ World Bible.

Không đưa future reveal nếu scene chưa được phép biết.

Context Preview phải cho tác giả thấy và bỏ/add item thủ công.

------------------------------------------------------------------------

# 38. CONTINUITY / IMPACT / RETCON

Khi tác giả sửa Canon cũ, app cần mô phỏng Impact.

Ví dụ: Tác giả đổi "Khách sạn từng có 8 tầng" thành "Historical Variant,
chưa chắc từng là current reality".

Impact panel:

-   Ch.1 affected.
-   Ch.5 affected.
-   Mystery M-002 affected.
-   Minh Knowledge affected.
-   Bà Lệ dialogue may need review.

Không tự rewrite hàng loạt trước khi tác giả duyệt.

Retcon workflow:

**Change → Impact Preview → Select affected items → AI proposal → Review
→ Apply**

------------------------------------------------------------------------

# 39. UI COPY MẪU

Badges:

`CANON` `PLANNED` `HYPOTHESIS` `VARIANT` `UNKNOWN` `WHAT-IF`

Warnings:

> Minh chưa biết điều này ở Ch.9.

> Chi tiết này mâu thuẫn Current Reality.

> Đây là giả thuyết, không phải Canon.

> AI đang đề xuất một quan hệ mới.

> Reveal này được lên kế hoạch cho Ch.27.

Buttons:

`Expand with AI` `Preview Plan` `Preview Context` `Review Changes`
`Approve to Canon` `Keep as Planned` `Save as What-if`
`Check Continuity`

------------------------------------------------------------------------

# 40. TIÊU CHÍ MOCKUP THÀNH CÔNG

Mockup thành công nếu nhìn vào sản phẩm người dùng hiểu ngay:

1.  Đây là app viết tiểu thuyết dài, không phải chatbot có editor.
2.  Tác giả kiểm soát Canon.
3.  AI biết đúng lượng context cần thiết.
4.  App biết nhân vật ở từng thời điểm biết gì.
5.  App có thể quản lý mystery mà không tự giải.
6.  App phân biệt câu hỏi triết học với plot hole.
7.  App hỗ trợ quan hệ thay đổi theo thời gian.
8.  AI viết xong không tự cập nhật thế giới.
9.  Người dùng có thể kiểm tra impact trước retcon.
10. Mobile/iPad là trải nghiệm chính.
11. Light và Dark là hai hệ giao diện thực sự.
12. Project Vĩnh Thành trông giống một dự án đang được viết thật, không
    phải lorem ipsum/demo rỗng.

------------------------------------------------------------------------

# 41. CHỈ DẪN CHO AI TẠO MOCKUP

Hãy tạo một mockup/prototype có dữ liệu thật từ spec này.

Không đơn giản hóa thành: - editor + chat; - danh sách character tĩnh; -
world wiki; - dashboard chỉ có card trang trí.

Ưu tiên thể hiện workflow thực tế của tác giả.

Nếu cần giảm scope ở vòng đầu, ưu tiên theo thứ tự:

**P0** 1. Project Dashboard. 2. Chapter Tree. 3. Write. 4. Author Brief.
5. Preview Context. 6. AI Expand. 7. After-write Review. 8.
Canon/Continuity. 9. Character temporal state. 10. Mystery Tracker.

**P1** 11. World. 12. Relationships. 13. Timeline. 14. AI Discussion.
15. What-if.

**P2** 16. Impact/Retcon. 17. Account/API/Credit. 18. Export/import.

Mockup phải có navigation hoạt động giữa các màn hình chính và sử dụng
Vĩnh Thành làm dữ liệu xuyên suốt.

Không tự bổ sung lời giải cuối cùng cho các mystery của Vĩnh Thành.
Không biến speculative/philosophical question thành Canon. Không biến
truyện thành horror ma quỷ.

------------------------------------------------------------------------

# 42. PROMPT NGẮN ĐỂ GIAO CHO AI BUILD

Bạn đang xây mockup cho **AI Writer Studio**, một ứng dụng mobile/iPad
hỗ trợ tác giả viết tiểu thuyết dài bằng AI.

Đọc toàn bộ file spec này trước khi thiết kế.

Dùng **Vĩnh Thành** làm project demo thật.

Mục tiêu quan trọng nhất không phải tạo giao diện đẹp đơn thuần mà phải
chứng minh workflow:

**Author Brief → Preview Plan → Preview Context → AI Expand → Continuity
Review → Author Approval → Canon Update.**

Hệ thống phải phân biệt: **Canon / Planned / Hypothesis / Variant /
Character Knowledge / Character Memory / Current Reality / What-if.**

Không để AI tự quyết Canon.

Thiết kế mobile-first và iPad-first; không desktop-first.

Tạo Light và Dark Mode thực sự.

Ưu tiên trải nghiệm viết, Chapter Tree, Context Builder, temporal
character state, Mystery Tracker và Continuity Engine.

Dữ liệu Vĩnh Thành trong file này là source of truth cho mockup. Không
tự giải các mystery chưa được khóa.
