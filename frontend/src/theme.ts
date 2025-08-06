// frontend/src/theme.ts

// Color palette
export const colors = {
    // Primary colors
    primary: {
      50: '#eff6ff',
      100: '#dbeafe',
      200: '#bfdbfe',
      300: '#93c5fd',
      400: '#60a5fa',
      500: '#3b82f6',
      600: '#2563eb',
      700: '#1d4ed8',
      800: '#1e40af',
      900: '#1e3a8a',
    },
    
    // Secondary colors
    secondary: {
      50: '#f8fafc',
      100: '#f1f5f9',
      200: '#e2e8f0',
      300: '#cbd5e1',
      400: '#94a3b8',
      500: '#64748b',
      600: '#475569',
      700: '#334155',
      800: '#1e293b',
      900: '#0f172a',
    },
    
    // Success colors
    success: {
      50: '#f0fdf4',
      100: '#dcfce7',
      200: '#bbf7d0',
      300: '#86efac',
      400: '#4ade80',
      500: '#22c55e',
      600: '#16a34a',
      700: '#15803d',
      800: '#166534',
      900: '#14532d',
    },
    
    // Warning colors
    warning: {
      50: '#fffbeb',
      100: '#fef3c7',
      200: '#fde68a',
      300: '#fcd34d',
      400: '#fbbf24',
      500: '#f59e0b',
      600: '#d97706',
      700: '#b45309',
      800: '#92400e',
      900: '#78350f',
    },
    
    // Error colors
    error: {
      50: '#fef2f2',
      100: '#fee2e2',
      200: '#fecaca',
      300: '#fca5a5',
      400: '#f87171',
      500: '#ef4444',
      600: '#dc2626',
      700: '#b91c1c',
      800: '#991b1b',
      900: '#7f1d1d',
    },
    
    // Info colors
    info: {
      50: '#f0f9ff',
      100: '#e0f2fe',
      200: '#bae6fd',
      300: '#7dd3fc',
      400: '#38bdf8',
      500: '#0ea5e9',
      600: '#0284c7',
      700: '#0369a1',
      800: '#075985',
      900: '#0c4a6e',
    },
    
    // Neutral colors
    gray: {
      50: '#f9fafb',
      100: '#f3f4f6',
      200: '#e5e7eb',
      300: '#d1d5db',
      400: '#9ca3af',
      500: '#6b7280',
      600: '#4b5563',
      700: '#374151',
      800: '#1f2937',
      900: '#111827',
    },
    
    // Fantasy-specific colors
    fantasy: {
      gold: '#ffd700',
      silver: '#c0c0c0',
      bronze: '#cd7f32',
    },
    
    // Position colors
    positions: {
      GK: '#8b5cf6',  // Purple
      DEF: '#3b82f6', // Blue
      MID: '#10b981', // Green
      FWD: '#f59e0b', // Orange
    },
    
    // Team status colors
    teamStatus: {
      winning: '#22c55e',
      losing: '#ef4444',
      neutral: '#6b7280',
    }
  };
  
  // Typography
  export const typography = {
    fontFamily: {
      primary: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif",
      mono: "'Fira Code', 'Monaco', 'Consolas', monospace",
    },
    
    fontSize: {
      xs: '0.75rem',     // 12px
      sm: '0.875rem',    // 14px
      base: '1rem',      // 16px
      lg: '1.125rem',    // 18px
      xl: '1.25rem',     // 20px
      '2xl': '1.5rem',   // 24px
      '3xl': '1.875rem', // 30px
      '4xl': '2.25rem',  // 36px
      '5xl': '3rem',     // 48px
    },
    
    fontWeight: {
      light: 300,
      normal: 400,
      medium: 500,
      semibold: 600,
      bold: 700,
      extrabold: 800,
    },
    
    lineHeight: {
      tight: 1.25,
      normal: 1.5,
      relaxed: 1.75,
    }
  };
  
  // Spacing
  export const spacing = {
    0: '0',
    1: '0.25rem',  // 4px
    2: '0.5rem',   // 8px
    3: '0.75rem',  // 12px
    4: '1rem',     // 16px
    5: '1.25rem',  // 20px
    6: '1.5rem',   // 24px
    8: '2rem',     // 32px
    10: '2.5rem',  // 40px
    12: '3rem',    // 48px
    16: '4rem',    // 64px
    20: '5rem',    // 80px
    24: '6rem',    // 96px
  };
  
  // Border radius
  export const borderRadius = {
    none: '0',
    sm: '0.125rem',  // 2px
    base: '0.25rem', // 4px
    md: '0.375rem',  // 6px
    lg: '0.5rem',    // 8px
    xl: '0.75rem',   // 12px
    '2xl': '1rem',   // 16px
    '3xl': '1.5rem', // 24px
    full: '9999px',
  };
  
  // Shadows
  export const shadows = {
    sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
    base: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
    md: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
    lg: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
    xl: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
    '2xl': '0 25px 50px -12px rgb(0 0 0 / 0.25)',
    inner: 'inset 0 2px 4px 0 rgb(0 0 0 / 0.05)',
    none: 'none',
  };
  
  // Breakpoints
  export const breakpoints = {
    sm: '640px',
    md: '768px',
    lg: '1024px',
    xl: '1280px',
    '2xl': '1536px',
  };
  
  // Z-index values
  export const zIndex = {
    auto: 'auto',
    0: 0,
    10: 10,
    20: 20,
    30: 30,
    40: 40,
    50: 50,
    dropdown: 1000,
    sticky: 1020,
    fixed: 1030,
    modal: 1040,
    popover: 1050,
    tooltip: 1060,
    toast: 1070,
  };
  
  // Animation durations
  export const duration = {
    75: '75ms',
    100: '100ms',
    150: '150ms',
    200: '200ms',
    300: '300ms',
    500: '500ms',
    700: '700ms',
    1000: '1000ms',
  };
  
  // Component-specific themes
  export const components = {
    // Button variants
    button: {
      variants: {
        primary: {
          backgroundColor: colors.primary[600],
          color: '#ffffff',
          hover: {
            backgroundColor: colors.primary[700],
          },
        },
        secondary: {
          backgroundColor: colors.secondary[100],
          color: colors.secondary[900],
          hover: {
            backgroundColor: colors.secondary[200],
          },
        },
        success: {
          backgroundColor: colors.success[600],
          color: '#ffffff',
          hover: {
            backgroundColor: colors.success[700],
          },
        },
        warning: {
          backgroundColor: colors.warning[600],
          color: '#ffffff',
          hover: {
            backgroundColor: colors.warning[700],
          },
        },
        error: {
          backgroundColor: colors.error[600],
          color: '#ffffff',
          hover: {
            backgroundColor: colors.error[700],
          },
        },
        outline: {
          backgroundColor: 'transparent',
          color: colors.primary[600],
          border: `1px solid ${colors.primary[600]}`,
          hover: {
            backgroundColor: colors.primary[50],
          },
        },
      },
      sizes: {
        sm: {
          padding: `${spacing[2]} ${spacing[3]}`,
          fontSize: typography.fontSize.sm,
        },
        md: {
          padding: `${spacing[3]} ${spacing[4]}`,
          fontSize: typography.fontSize.base,
        },
        lg: {
          padding: `${spacing[4]} ${spacing[6]}`,
          fontSize: typography.fontSize.lg,
        },
      },
    },
    
    // Card styles
    card: {
      backgroundColor: '#ffffff',
      borderRadius: borderRadius.lg,
      boxShadow: shadows.base,
      border: `1px solid ${colors.gray[200]}`,
      padding: spacing[6],
    },
    
    // Input styles
    input: {
      backgroundColor: '#ffffff',
      border: `1px solid ${colors.gray[300]}`,
      borderRadius: borderRadius.md,
      padding: `${spacing[3]} ${spacing[4]}`,
      fontSize: typography.fontSize.base,
      focus: {
        borderColor: colors.primary[500],
        boxShadow: `0 0 0 3px ${colors.primary[500]}20`,
        outline: 'none',
      },
    },
    
    // Modal styles
    modal: {
      overlay: {
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        zIndex: zIndex.modal,
      },
      content: {
        backgroundColor: '#ffffff',
        borderRadius: borderRadius.lg,
        boxShadow: shadows.xl,
        maxWidth: '90vw',
        maxHeight: '90vh',
      },
    },
  };
  
  // Layout grid
  export const grid = {
    container: {
      maxWidth: {
        sm: '640px',
        md: '768px',
        lg: '1024px',
        xl: '1280px',
        '2xl': '1536px',
      },
      padding: {
        sm: spacing[4],
        md: spacing[6],
        lg: spacing[8],
      },
    },
    
    columns: {
      1: '100%',
      2: '50%',
      3: '33.333333%',
      4: '25%',
      5: '20%',
      6: '16.666667%',
      12: '8.333333%',
    },
  };
  
  // Fantasy-specific styling
  export const fantasy = {
    // Player card styling
    playerCard: {
      backgroundColor: '#ffffff',
      border: `1px solid ${colors.gray[200]}`,
      borderRadius: borderRadius.lg,
      padding: spacing[4],
      hover: {
        borderColor: colors.primary[300],
        boxShadow: shadows.md,
      },
    },
    
    // Draft board styling
    draftBoard: {
      grid: {
        backgroundColor: colors.gray[50],
        borderColor: colors.gray[300],
      },
      cell: {
        backgroundColor: '#ffffff',
        border: `1px solid ${colors.gray[200]}`,
        padding: spacing[2],
      },
      selectedCell: {
        backgroundColor: colors.primary[50],
        borderColor: colors.primary[300],
      },
    },
    
    // Team colors (can be customized per team)
    teamColors: [
      '#ef4444', // Red
      '#3b82f6', // Blue
      '#10b981', // Green
      '#f59e0b', // Orange
      '#8b5cf6', // Purple
      '#ec4899', // Pink
      '#06b6d4', // Cyan
      '#84cc16', // Lime
      '#f97316', // Orange
      '#6366f1', // Indigo
      '#14b8a6', // Teal
      '#eab308', // Yellow
    ],
  };
  
  // Export complete theme object
  export const theme = {
    colors,
    typography,
    spacing,
    borderRadius,
    shadows,
    breakpoints,
    zIndex,
    duration,
    components,
    grid,
    fantasy,
  };
  
  export default theme;