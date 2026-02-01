import { createI18n } from 'vue-i18n'
import zhCN from './locales/zh-CN.json'
import zhTW from './locales/zh-TW.json'
import en from './locales/en.json'
import ja from './locales/ja.json'

// Get language from localStorage or user preference
const getLocale = () => {
    const user = JSON.parse(localStorage.getItem('user') || '{}')
    return user.language || localStorage.getItem('language') || 'zh-CN'
}

const i18n = createI18n({
    legacy: false,
    locale: getLocale(),
    fallbackLocale: 'en',
    messages: {
        'zh-CN': zhCN,
        'zh-TW': zhTW,
        'en': en,
        'ja': ja
    }
})

export default i18n
