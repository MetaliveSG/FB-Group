// Customer app i18n boundary — wraps every /t page (storefront + group browse) in the LocaleProvider
// so useT()/useLocale() work app-wide. The provider self-initialises from the saved choice → device
// language (clamped); a diner's language never moves prices or times (those are place/settlement facts).
import { LocaleProvider } from "@fbgroup/i18n";

export default function CustomerLayout({ children }: { children: React.ReactNode }) {
  return <LocaleProvider>{children}</LocaleProvider>;
}
