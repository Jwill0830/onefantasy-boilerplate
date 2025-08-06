/**
 * Utility functions for formatting data display
 */

// Format player price
export const formatPrice = (price: number): string => {
    return `£${(price / 10).toFixed(1)}m`;
  };
  
  // Format percentage
  export const formatPercentage = (value: number): string => {
    return `${value.toFixed(1)}%`;
  };
  
  // Format large numbers with abbreviations
  export const formatNumber = (num: number): string => {
    if (num >= 1000000) {
      return `${(num / 1000000).toFixed(1)}M`;
    } else if (num >= 1000) {
      return `${(num / 1000).toFixed(1)}K`;
    } else {
      return num.toString();
    }
  };
  
  // Format date relative to now
  export const formatRelativeTime = (date: Date): string => {
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const diffMinutes = Math.floor(diff / (1000 * 60));
    const diffHours = Math.floor(diff / (1000 * 60 * 60));
    const diffDays = Math.floor(diff / (1000 * 60 * 60 * 24));
  
    if (diffMinutes < 1) {
      return 'Just now';
    } else if (diffMinutes < 60) {
      return `${diffMinutes}m ago`;
    } else if (diffHours < 24) {
      return `${diffHours}h ago`;
    } else if (diffDays < 7) {
      return `${diffDays}d ago`;
    } else {
      return date.toLocaleDateString();
    }
  };
  
  // Format date and time
  export const formatDateTime = (date: Date): string => {
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  };
  
  // Format date only
  export const formatDate = (date: Date): string => {
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    }).format(date);
  };
  
  // Format time only
  export const formatTime = (date: Date): string => {
    return new Intl.DateTimeFormat('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  };
  
  // Format duration in seconds to readable format
  export const formatDuration = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
  
    if (hours > 0) {
      return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
      return `${minutes}m ${secs}s`;
    } else {
      return `${secs}s`;
    }
  };
  
  // Format points with ordinal suffix
  export const formatOrdinal = (num: number): string => {
    const suffix = ['th', 'st', 'nd', 'rd'];
    const value = num % 100;
    return num + (suffix[(value - 20) % 10] || suffix[value] || suffix[0]);
  };
  
  // Format team record (wins-losses-draws)
  export const formatRecord = (wins: number, losses: number, draws: number): string => {
    return `${wins}-${losses}-${draws}`;
  };
  
  // Format win percentage
  export const formatWinPercentage = (wins: number, total: number): string => {
    if (total === 0) return '0.0%';
    return `${((wins / total) * 100).toFixed(1)}%`;
  };
  
  // Format player form (decimal to 1 place)
  export const formatForm = (form: number): string => {
    return form.toFixed(1);
  };
  
  // Format player points per game
  export const formatPointsPerGame = (ppg: number): string => {
    return ppg.toFixed(1);
  };
  
  // Format player ICT index
  export const formatICT = (ict: number): string => {
    return ict.toFixed(1);
  };
  
  // Format currency (for waiver budgets)
  export const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };
  
  // Format list of items with proper grammar
  export const formatList = (items: string[]): string => {
    if (items.length === 0) return '';
    if (items.length === 1) return items[0];
    if (items.length === 2) return `${items[0]} and ${items[1]}`;
    
    const lastItem = items[items.length - 1];
    const firstItems = items.slice(0, -1);
    return `${firstItems.join(', ')}, and ${lastItem}`;
  };
  
  // Format gameweek with prefix
  export const formatGameweek = (gameweek: number): string => {
    return `GW${gameweek}`;
  };
  
  // Format season with proper formatting
  export const formatSeason = (startYear: number): string => {
    return `${startYear}/${(startYear + 1).toString().slice(-2)}`;
  };
  
  // Format position with full name
  export const formatPosition = (position: string): string => {
    const positions: Record<string, string> = {
      'GKP': 'Goalkeeper',
      'DEF': 'Defender', 
      'MID': 'Midfielder',
      'FWD': 'Forward',
    };
    return positions[position] || position;
  };
  
  // Format availability status
  export const formatAvailability = (chance: number | null): string => {
    if (chance === null || chance === 100) return 'Available';
    if (chance === 0) return 'Unavailable';
    if (chance <= 25) return 'Doubtful';
    if (chance <= 75) return 'Uncertain';
    return 'Likely';
  };
  
  // Format score difference
  export const formatScoreDifference = (difference: number): string => {
    if (difference > 0) return `+${difference}`;
    return difference.toString();
  };
  
  // Format trade status
  export const formatTradeStatus = (status: string): string => {
    const statuses: Record<string, string> = {
      'proposed': 'Pending',
      'accepted': 'Accepted',
      'rejected': 'Rejected',
      'cancelled': 'Cancelled',
      'expired': 'Expired',
      'completed': 'Completed',
    };
    return statuses[status] || status;
  };