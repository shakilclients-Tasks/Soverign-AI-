import { useEffect, useState } from 'react'

export type Theme = 'dark' | 'bright'

const THEME_STORAGE_KEY = 'sovereign_theme'

export function useTheme() {
  const [theme, setThemeState] = useState<Theme>(() => {
    if (typeof window === 'undefined') return 'dark'
    const stored = localStorage.getItem(THEME_STORAGE_KEY)
    if (stored === 'bright' || stored === 'dark') return stored
    return 'dark'
  })

  useEffect(() => {
    const root = document.documentElement
    if (theme === 'bright') {
      root.classList.add('bright')
      root.classList.remove('dark')
      root.style.colorScheme = 'light'
    } else {
      root.classList.add('dark')
      root.classList.remove('bright')
      root.style.colorScheme = 'dark'
    }
    localStorage.setItem(THEME_STORAGE_KEY, theme)
  }, [theme])

  const toggleTheme = () => {
    setThemeState((current) => (current === 'dark' ? 'bright' : 'dark'))
  }

  const setTheme = (next: Theme) => {
    setThemeState(next)
  }

  return { theme, toggleTheme, setTheme, isBright: theme === 'bright' }
}
