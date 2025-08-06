/**
 * Utility functions for form validation
 */

// Email validation
export const isValidEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };
  
  // Password validation
  export const isValidPassword = (password: string): boolean => {
    // At least 8 characters, 1 uppercase, 1 lowercase, 1 number
    const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[a-zA-Z\d@$!%*?&]{8,}$/;
    return passwordRegex.test(password);
  };
  
  // Team name validation
  export const isValidTeamName = (name: string): boolean => {
    return name.trim().length >= 2 && name.trim().length <= 50;
  };
  
  // League name validation
  export const isValidLeagueName = (name: string): boolean => {
    return name.trim().length >= 3 && name.trim().length <= 100;
  };
  
  // Validate lineup formation
  export const isValidLineup = (lineup: {
    starting_11: number[];
    bench: number[];
    captain: number;
    vice_captain: number;
  }): { valid: boolean; errors: string[] } => {
    const errors: string[] = [];
  
    // Check starting 11 count
    if (lineup.starting_11.length !== 11) {
      errors.push('Starting 11 must contain exactly 11 players');
    }
  
    // Check bench count
    if (lineup.bench.length > 4) {
      errors.push('Bench can contain maximum 4 players');
    }
  
    // Check captain is in starting 11
    if (!lineup.starting_11.includes(lineup.captain)) {
      errors.push('Captain must be in starting 11');
    }
  
    // Check vice captain is in starting 11
    if (!lineup.starting_11.includes(lineup.vice_captain)) {
      errors.push('Vice captain must be in starting 11');
    }
  
    // Check captain and vice captain are different
    if (lineup.captain === lineup.vice_captain) {
      errors.push('Captain and vice captain must be different players');
    }
  
    // Check for duplicate players
    const allPlayers = [...lineup.starting_11, ...lineup.bench];
    const uniquePlayers = new Set(allPlayers);
    if (uniquePlayers.size !== allPlayers.length) {
      errors.push('Duplicate players in lineup');
    }
  
    return {
      valid: errors.length === 0,
      errors
    };
  };
  
  // Validate waiver bid amount
  export const isValidWaiverBid = (bid: number, budget: number): { valid: boolean; error?: string } => {
    if (bid < 0) {
      return { valid: false, error: 'Bid amount cannot be negative' };
    }
  
    if (bid > budget) {
      return { valid: false, error: 'Bid amount exceeds available budget' };
    }
  
    if (!Number.isInteger(bid)) {
      return { valid: false, error: 'Bid amount must be a whole number' };
    }
  
    return { valid: true };
  };
  
  // Validate trade proposal
  export const isValidTradeProposal = (
    proposerPlayers: number[],
    targetPlayers: number[]
  ): { valid: boolean; errors: string[] } => {
    const errors: string[] = [];
  
    // At least one player must be involved
    if (proposerPlayers.length === 0 && targetPlayers.length === 0) {
      errors.push('Trade must include at least one player');
    }
  
    // Maximum players per side
    if (proposerPlayers.length > 5) {
      errors.push('Maximum 5 players per team in trade');
    }
  
    if (targetPlayers.length > 5) {
      errors.push('Maximum 5 players per team in trade');
    }
  
    // Check for duplicate players
    const proposerSet = new Set(proposerPlayers);
    const targetSet = new Set(targetPlayers);
  
    if (proposerSet.size !== proposerPlayers.length) {
      errors.push('Duplicate players in proposer side');
    }
  
    if (targetSet.size !== targetPlayers.length) {
      errors.push('Duplicate players in target side');
    }
  
    // Check no player appears on both sides
    const intersection = new Set([...proposerSet].filter(x => targetSet.has(x)));
    if (intersection.size > 0) {
      errors.push('Players cannot appear on both sides of trade');
    }
  
    return {
      valid: errors.length === 0,
      errors
    };
  };
  
  // Validate price range
  export const isValidPriceRange = (min?: number, max?: number): { valid: boolean; error?: string } => {
    if (min !== undefined && min < 0) {
      return { valid: false, error: 'Minimum price cannot be negative' };
    }
  
    if (max !== undefined && max < 0) {
      return { valid: false, error: 'Maximum price cannot be negative' };
    }
  
    if (min !== undefined && max !== undefined && min > max) {
      return { valid: false, error: 'Minimum price cannot be greater than maximum price' };
    }
  
    return { valid: true };
  };
  
  // Validate points range
  export const isValidPointsRange = (min?: number, max?: number): { valid: boolean; error?: string } => {
    if (min !== undefined && min < 0) {
      return { valid: false, error: 'Minimum points cannot be negative' };
    }
  
    if (max !== undefined && max < 0) {
      return { valid: false, error: 'Maximum points cannot be negative' };
    }
  
    if (min !== undefined && max !== undefined && min > max) {
      return { valid: false, error: 'Minimum points cannot be greater than maximum points' };
    }
  
    return { valid: true };
  };
  
  // Validate form value
  export const isValidForm = (form: number): boolean => {
    return form >= 0 && form <= 10;
  };
  
  // Validate gameweek number
  export const isValidGameweek = (gameweek: number): boolean => {
    return gameweek >= 1 && gameweek <= 38;
  };
  
  // Validate league size
  export const isValidLeagueSize = (size: number): boolean => {
    return size >= 6 && size <= 18;
  };
  
  // Validate draft settings
  export const isValidDraftSettings = (settings: {
    rounds?: number;
    pick_duration?: number;
    draft_type?: string;
  }): { valid: boolean; errors: string[] } => {
    const errors: string[] = [];
  
    if (settings.rounds !== undefined) {
      if (settings.rounds < 10 || settings.rounds > 20) {
        errors.push('Draft rounds must be between 10 and 20');
      }
    }
  
    if (settings.pick_duration !== undefined) {
      if (settings.pick_duration < 30 || settings.pick_duration > 300) {
        errors.push('Pick duration must be between 30 and 300 seconds');
      }
    }
  
    if (settings.draft_type !== undefined) {
      const validTypes = ['snake', 'linear', 'random'];
      if (!validTypes.includes(settings.draft_type)) {
        errors.push('Invalid draft type');
      }
    }
  
    return {
      valid: errors.length === 0,
      errors
    };
  };
  
  // Validate URL
  export const isValidUrl = (url: string): boolean => {
    try {
      new URL(url);
      return true;
    } catch {
      return false;
    }
  };
  
  // Validate image URL (basic check)
  export const isValidImageUrl = (url: string): boolean => {
    if (!isValidUrl(url)) return false;
    
    const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'];
    const lowercaseUrl = url.toLowerCase();
    
    return imageExtensions.some(ext => lowercaseUrl.includes(ext)) || 
           lowercaseUrl.includes('image') ||
           lowercaseUrl.includes('img') ||
           lowercaseUrl.includes('avatar') ||
           lowercaseUrl.includes('logo');
  };
  
  // Validate date is in the future
  export const isValidFutureDate = (date: Date): boolean => {
    return date.getTime() > new Date().getTime();
  };
  
  // Validate date range
  export const isValidDateRange = (start: Date, end: Date): { valid: boolean; error?: string } => {
    if (start.getTime() >= end.getTime()) {
      return { valid: false, error: 'Start date must be before end date' };
    }
  
    return { valid: true };
  };
  
  // Validate hex color code
  export const isValidHexColor = (color: string): boolean => {
    const hexRegex = /^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$/;
    return hexRegex.test(color);
  };
  
  // Validate positive number
  export const isValidPositiveNumber = (value: number): boolean => {
    return typeof value === 'number' && value > 0 && !isNaN(value);
  };
  
  // Validate non-negative number
  export const isValidNonNegativeNumber = (value: number): boolean => {
    return typeof value === 'number' && value >= 0 && !isNaN(value);
  };
  
  // Validate integer
  export const isValidInteger = (value: number): boolean => {
    return Number.isInteger(value);
  };
  
  // Validate string length
  export const isValidStringLength = (str: string, min: number, max: number): boolean => {
    const length = str.trim().length;
    return length >= min && length <= max;
  };
  
  // Validate required field
  export const isRequired = (value: any): boolean => {
    if (value === null || value === undefined) return false;
    if (typeof value === 'string') return value.trim().length > 0;
    if (Array.isArray(value)) return value.length > 0;
    return true;
  };
  
  // Validate array of unique values
  export const hasUniqueValues = (arr: any[]): boolean => {
    return new Set(arr).size === arr.length;
  };
  
  // Validate object has required keys
  export const hasRequiredKeys = (obj: object, requiredKeys: string[]): { valid: boolean; missing: string[] } => {
    const objectKeys = Object.keys(obj);
    const missing = requiredKeys.filter(key => !objectKeys.includes(key));
    
    return {
      valid: missing.length === 0,
      missing
    };
  };