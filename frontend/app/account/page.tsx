import Link from "next/link";
import ProfileForm from "../../components/ProfileForm";
import ThemeToggle from "../../components/ThemeToggle";
import LangToggle from "../../components/LangToggle";
import { getLang } from "../../lib/lang-server";
import { t } from "../../lib/i18n";

export default async function AccountPage() {
  const lang = await getLang();
  return (
    <div className="app">
      <header className="top">
        <Link href="/" className="brand" style={{ textDecoration: "none" }}>
          <span className="mark">A</span> AI Writer Studio
        </Link>
        <span className="crumb">{t(lang, "Tài khoản")}</span>
        <Link href="/settings" className="account-shortcut" style={{ textDecoration: "none", marginLeft: "auto" }}>
          {t(lang, "Kết nối API")}
        </Link>
        <LangToggle />
        <ThemeToggle />
      </header>
      <main className="page"><div className="dashboard settings-screen">
        <div className="dash-head">
          <div>
            <div className="eyebrow">{t(lang, "Cài đặt")}</div>
            <h1>{t(lang, "Tài khoản & Credit")}</h1>
          </div>
        </div>
        <div className="settings-grid">
          <div className="card">
            <h3>{t(lang, "Hồ sơ")}</h3>
            <p className="settings-note">
              {t(lang, "Thông tin trên thiết bị này. Đăng nhập và đồng bộ tài khoản sẽ được kết nối khi có máy chủ.")}
            </p>
            <ProfileForm />
          </div>
          <div className="card">
            <h3>Credit</h3>
            <div className="credit-balance"><b>0</b><span>{t(lang, "credit khả dụng")}</span></div>
            <p className="settings-note">
              {t(lang, "Chưa có hệ thống tính credit hoặc thanh toán. Việc tạo bản nháp hiện không trừ credit.")}
            </p>
            <div className="credit-history">{t(lang, "Lịch sử sử dụng: chưa có giao dịch.")}</div>
          </div>
        </div>
      </div></main>
    </div>
  );
}
