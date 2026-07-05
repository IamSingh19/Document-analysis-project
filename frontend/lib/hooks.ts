import { useEffect, useState } from 'react'

/**
 * Hook to handle Zustand store hydration in Next.js
 * This prevents hydration mismatch errors and ensures localStorage is read
 */
export function useHydration() {
  const [isHydrated, setIsHydrated] = useState(false)

  useEffect(() => {
    setIsHydrated(true)
  }, [])

  return isHydrated
}
