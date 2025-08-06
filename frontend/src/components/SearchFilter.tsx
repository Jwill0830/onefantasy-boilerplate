/**
 * SearchFilter component - Advanced filtering interface for players
 */

import React, { useState, useEffect } from 'react';

// Define PlayerFilters interface locally since it's not exported from types
interface PlayerFilters {
  position?: string[];
  team?: string[];
  minPrice?: number;
  maxPrice?: number;
  minPoints?: number;
  maxPoints?: number;
  minForm?: number;
  availableOnly?: boolean;
  excludeInjured?: boolean;
  limit?: number;
  searchTerm?: string;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

interface SearchFilterProps {
  onFiltersChange: (filters: PlayerFilters) => void;
  onSearch: (query: string) => void;
  initialFilters?: Partial<PlayerFilters>;
  showAdvanced?: boolean;
  className?: string;
  positions?: string[];
  showTeamFilter?: boolean;
  disabled?: boolean;
}

const SearchFilter: React.FC<SearchFilterProps> = ({
  onFiltersChange,
  onSearch,
  initialFilters = {},
  showAdvanced = true,
  className = '',
  positions = ['GKP', 'DEF', 'MID', 'FWD'],
  showTeamFilter = true,
  disabled = false,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [filters, setFilters] = useState<PlayerFilters>({
    position: [],
    team: [],
    minPrice: undefined,
    maxPrice: undefined,
    minPoints: undefined,
    maxPoints: undefined,
    minForm: undefined,
    availableOnly: false,
    excludeInjured: false,
    limit: 50,
    ...initialFilters,
  });

  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [debouncedQuery, setDebouncedQuery] = useState('');

  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery);
    }, 300);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Trigger search when debounced query changes
  useEffect(() => {
    onSearch(debouncedQuery);
  }, [debouncedQuery, onSearch]);

  // Trigger filters change when filters update
  useEffect(() => {
    onFiltersChange(filters);
  }, [filters, onFiltersChange]);

  const positionOptions = [
    { value: 'GKP', label: 'Goalkeeper' },
    { value: 'DEF', label: 'Defender' },
    { value: 'MID', label: 'Midfielder' },
    { value: 'FWD', label: 'Forward' },
  ].filter(pos => positions.includes(pos.value));

  const teams = [
    { value: 'ARS', label: 'Arsenal' },
    { value: 'AVL', label: 'Aston Villa' },
    { value: 'BOU', label: 'Bournemouth' },
    { value: 'BRE', label: 'Brentford' },
    { value: 'BHA', label: 'Brighton' },
    { value: 'BUR', label: 'Burnley' },
    { value: 'CHE', label: 'Chelsea' },
    { value: 'CRY', label: 'Crystal Palace' },
    { value: 'EVE', label: 'Everton' },
    { value: 'FUL', label: 'Fulham' },
    { value: 'LIV', label: 'Liverpool' },
    { value: 'LUT', label: 'Luton' },
    { value: 'MCI', label: 'Man City' },
    { value: 'MUN', label: 'Man Utd' },
    { value: 'NEW', label: 'Newcastle' },
    { value: 'NFO', label: 'Nott\'m Forest' },
    { value: 'SHU', label: 'Sheffield Utd' },
    { value: 'TOT', label: 'Spurs' },
    { value: 'WHU', label: 'West Ham' },
    { value: 'WOL', label: 'Wolves' },
  ];

  const handlePositionToggle = (position: string) => {
    if (disabled) return;
    
    setFilters(prev => ({
      ...prev,
      position: prev.position?.includes(position)
        ? prev.position.filter(p => p !== position)
        : [...(prev.position || []), position],
    }));
  };

  const handleTeamToggle = (team: string) => {
    if (disabled) return;
    
    setFilters(prev => ({
      ...prev,
      team: prev.team?.includes(team)
        ? prev.team.filter(t => t !== team)
        : [...(prev.team || []), team],
    }));
  };

  const clearFilters = () => {
    if (disabled) return;
    
    setFilters({
      position: [],
      team: [],
      minPrice: undefined,
      maxPrice: undefined,
      minPoints: undefined,
      maxPoints: undefined,
      minForm: undefined,
      availableOnly: false,
      excludeInjured: false,
      limit: 50,
    });
    setSearchQuery('');
  };

  const hasActiveFilters = () => {
    return (
      (filters.position?.length || 0) > 0 ||
      (filters.team?.length || 0) > 0 ||
      filters.minPrice !== undefined ||
      filters.maxPrice !== undefined ||
      filters.minPoints !== undefined ||
      filters.maxPoints !== undefined ||
      filters.minForm !== undefined ||
      filters.availableOnly ||
      filters.excludeInjured ||
      searchQuery.length > 0
    );
  };

  return (
    <div className={`bg-white border border-gray-200 rounded-lg p-4 ${disabled ? 'opacity-50 pointer-events-none' : ''} ${className}`}>
      {/* Search Bar */}
      <div className="mb-4">
        <div className="relative">
          <input
            type="text"
            placeholder="Search players by name, team..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            disabled={disabled}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
          />
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
        </div>
      </div>

      {/* Quick Filters */}
      <div className="mb-4">
        <div className="flex flex-wrap gap-2 mb-3">
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={filters.availableOnly || false}
              onChange={(e) => !disabled && setFilters(prev => ({ ...prev, availableOnly: e.target.checked }))}
              disabled={disabled}
              className="mr-2 rounded border-gray-300 text-blue-600 focus:ring-blue-500 disabled:cursor-not-allowed"
            />
            <span className="text-sm text-gray-700">Available only</span>
          </label>
          
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={filters.excludeInjured || false}
              onChange={(e) => !disabled && setFilters(prev => ({ ...prev, excludeInjured: e.target.checked }))}
              disabled={disabled}
              className="mr-2 rounded border-gray-300 text-blue-600 focus:ring-blue-500 disabled:cursor-not-allowed"
            />
            <span className="text-sm text-gray-700">Exclude injured</span>
          </label>
        </div>

        {/* Position Filter */}
        <div className="mb-3">
          <label className="block text-sm font-medium text-gray-700 mb-2">Position</label>
          <div className="flex flex-wrap gap-2">
            {positionOptions.map(position => (
              <button
                key={position.value}
                onClick={() => handlePositionToggle(position.value)}
                disabled={disabled}
                className={`
                  px-3 py-1 text-sm rounded-full border transition-colors disabled:cursor-not-allowed
                  ${filters.position?.includes(position.value)
                    ? 'bg-blue-100 border-blue-500 text-blue-700'
                    : 'bg-gray-100 border-gray-300 text-gray-700 hover:bg-gray-200 disabled:hover:bg-gray-100'
                  }
                `}
              >
                {position.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Advanced Filters Toggle */}
      {showAdvanced && (
        <div className="mb-4">
          <button
            onClick={() => !disabled && setShowAdvancedFilters(!showAdvancedFilters)}
            disabled={disabled}
            className="flex items-center text-sm text-blue-600 hover:text-blue-800 disabled:text-gray-400 disabled:cursor-not-allowed"
          >
            <span>Advanced Filters</span>
            <svg
              className={`ml-1 h-4 w-4 transition-transform ${showAdvancedFilters ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        </div>
      )}

      {/* Advanced Filters */}
      {showAdvancedFilters && (
        <div className="space-y-4 border-t border-gray-200 pt-4">
          {/* Team Filter */}
          {showTeamFilter && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Team</label>
              <div className="max-h-40 overflow-y-auto">
                <div className="grid grid-cols-2 gap-1">
                  {teams.map(team => (
                    <label key={team.value} className="flex items-center text-sm">
                      <input
                        type="checkbox"
                        checked={filters.team?.includes(team.value) || false}
                        onChange={() => handleTeamToggle(team.value)}
                        disabled={disabled}
                        className="mr-2 rounded border-gray-300 text-blue-600 focus:ring-blue-500 disabled:cursor-not-allowed"
                      />
                      <span className="text-gray-700">{team.label}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Price Range */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Min Price (£m)</label>
              <input
                type="number"
                step="0.1"
                min="3.5"
                max="15.0"
                value={filters.minPrice ? (filters.minPrice / 10).toFixed(1) : ''}
                onChange={(e) => !disabled && setFilters(prev => ({ 
                  ...prev, 
                  minPrice: e.target.value ? parseFloat(e.target.value) * 10 : undefined 
                }))}
                disabled={disabled}
                className="w-full px-3 py-1 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
                placeholder="3.5"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Max Price (£m)</label>
              <input
                type="number"
                step="0.1"
                min="3.5"
                max="15.0"
                value={filters.maxPrice ? (filters.maxPrice / 10).toFixed(1) : ''}
                onChange={(e) => !disabled && setFilters(prev => ({ 
                  ...prev, 
                  maxPrice: e.target.value ? parseFloat(e.target.value) * 10 : undefined 
                }))}
                disabled={disabled}
                className="w-full px-3 py-1 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
                placeholder="15.0"
              />
            </div>
          </div>

          {/* Points Range */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Min Points</label>
              <input
                type="number"
                min="0"
                max="500"
                value={filters.minPoints || ''}
                onChange={(e) => !disabled && setFilters(prev => ({ 
                  ...prev, 
                  minPoints: e.target.value ? parseInt(e.target.value) : undefined 
                }))}
                disabled={disabled}
                className="w-full px-3 py-1 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
                placeholder="0"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Max Points</label>
              <input
                type="number"
                min="0"
                max="500"
                value={filters.maxPoints || ''}
                onChange={(e) => !disabled && setFilters(prev => ({ 
                  ...prev, 
                  maxPoints: e.target.value ? parseInt(e.target.value) : undefined 
                }))}
                disabled={disabled}
                className="w-full px-3 py-1 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
                placeholder="500"
              />
            </div>
          </div>

          {/* Form Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Min Form</label>
            <input
              type="number"
              step="0.1"
              min="0"
              max="10"
              value={filters.minForm || ''}
              onChange={(e) => !disabled && setFilters(prev => ({ 
                ...prev, 
                minForm: e.target.value ? parseFloat(e.target.value) : undefined 
              }))}
              disabled={disabled}
              className="w-full px-3 py-1 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
              placeholder="0.0"
            />
          </div>

          {/* Results Limit */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Results Limit</label>
            <select
              value={filters.limit || 50}
              onChange={(e) => !disabled && setFilters(prev => ({ ...prev, limit: parseInt(e.target.value) }))}
              disabled={disabled}
              className="w-full px-3 py-1 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
            >
              <option value={25}>25 results</option>
              <option value={50}>50 results</option>
              <option value={100}>100 results</option>
            </select>
          </div>
        </div>
      )}

      {/* Filter Summary */}
      {hasActiveFilters() && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-600">
              {(filters.position?.length || 0) + (filters.team?.length || 0)} filters active
            </span>
            <button
              onClick={clearFilters}
              disabled={disabled}
              className="text-sm text-red-600 hover:text-red-800 disabled:text-gray-400 disabled:cursor-not-allowed"
            >
              Clear all
            </button>
          </div>
          
          {/* Active Filter Tags */}
          <div className="flex flex-wrap gap-1">
            {filters.position?.map(pos => (
              <span key={pos} className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-blue-100 text-blue-800">
                {pos}
                {!disabled && (
                  <button
                    onClick={() => handlePositionToggle(pos)}
                    className="ml-1 text-blue-600 hover:text-blue-800"
                  >
                    ×
                  </button>
                )}
              </span>
            ))}
            {filters.team?.slice(0, 3).map(team => (
              <span key={team} className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-green-100 text-green-800">
                {team}
                {!disabled && (
                  <button
                    onClick={() => handleTeamToggle(team)}
                    className="ml-1 text-green-600 hover:text-green-800"
                  >
                    ×
                  </button>
                )}
              </span>
            ))}
            {(filters.team?.length || 0) > 3 && (
              <span className="px-2 py-1 rounded-full text-xs bg-gray-100 text-gray-600">
                +{(filters.team?.length || 0) - 3} more teams
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export { type PlayerFilters };
export default SearchFilter;