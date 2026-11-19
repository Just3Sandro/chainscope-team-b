import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// Vitest est configuré sans `globals` : le nettoyage automatique de
// @testing-library/react n'est pas enregistré — on le fait explicitement.
afterEach(() => {
  cleanup()
})
