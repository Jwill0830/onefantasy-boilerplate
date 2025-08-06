// frontend/src/components/TransactionHistory.tsx
import React, { useState, useEffect, useMemo } from 'react';
import { Transaction, Player, Team } from '../types';
import { formatDate, formatTime } from '../utils/formatters';

// Extended Transaction interface with additional properties for display
interface ExtendedTransaction extends Transaction {
  playersIn?: Player[];
  playersOut?: Player[];
  bidAmount?: number;
  tradeValue?: number;
  createdAt: string;
  teamName?: string;
  waiverPriority?: number;
  draftRound?: number;
  draftPick?: number;
  isProcessed?: boolean;
  processedAt?: string;
  note?: string;
  tradingPartner?: { name: string; id: string };
  tradeDetails?: {
    tradeId?: string;
    proposedAt?: string;
    acceptedAt?: string;
  };
}

interface TransactionHistoryProps {
  teamId: string;
  leagueId: string;
  onFetchTransactions: (teamId: string, filters?: TransactionFilters) => Promise<ExtendedTransaction[]>;
  showAllLeague?: boolean;
  compact?: boolean;
  maxItems?: number;
  className?: string;
}

interface TransactionFilters {
  type?: 'all' | 'trade' | 'waiver_claim' | 'free_agent_add' | 'drop' | 'draft';
  status?: 'all' | 'completed' | 'pending' | 'rejected';
  dateRange?: 'today' | 'week' | 'month' | 'season' | 'all';
  playerId?: string;
  playerName?: string;
  sortBy?: 'date' | 'type' | 'player' | 'value';
  sortOrder?: 'asc' | 'desc';
}

export const TransactionHistory: React.FC<TransactionHistoryProps> = ({
  teamId,
  leagueId,
  onFetchTransactions,
  showAllLeague = false,
  compact = false,
  maxItems = 50,
  className = ''
}) => {
  const [transactions, setTransactions] = useState<ExtendedTransaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState<TransactionFilters>({
    type: 'all',
    status: 'all',
    dateRange: 'season',
    sortBy: 'date',
    sortOrder: 'desc'
  });
  const [error, setError] = useState<string>('');
  const [expandedTransaction, setExpandedTransaction] = useState<string | null>(null);
  const [showFilters, setShowFilters] = useState(!compact);

  useEffect(() => {
    fetchTransactions();
  }, [teamId, filters]);

  const fetchTransactions = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await onFetchTransactions(teamId, filters);
      // Transform basic transactions to extended ones
      const extendedData: ExtendedTransaction[] = data.map(t => ({
        ...t,
        createdAt: t.timestamp, // Use timestamp as createdAt
        playersIn: [], // Will be populated by parent component
        playersOut: [], // Will be populated by parent component
        teamName: showAllLeague ? `Team ${teamId}` : undefined
      }));
      setTransactions(extendedData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch transactions');
    } finally {
      setLoading(false);
    }
  };

  // Filter and sort transactions
  const filteredTransactions = useMemo(() => {
    let filtered = [...transactions];

    // Apply filters
    if (filters.type && filters.type !== 'all') {
      filtered = filtered.filter(t => t.type === filters.type);
    }

    if (filters.status && filters.status !== 'all') {
      filtered = filtered.filter(t => t.status === filters.status);
    }

    if (filters.playerName) {
      const searchTerm = filters.playerName.toLowerCase();
      filtered = filtered.filter(t => 
        t.playersIn?.some(p => p.name.toLowerCase().includes(searchTerm)) ||
        t.playersOut?.some(p => p.name.toLowerCase().includes(searchTerm))
      );
    }

    // Apply date range filter
    if (filters.dateRange && filters.dateRange !== 'all') {
      const now = new Date();
      const cutoffDate = new Date();

      switch (filters.dateRange) {
        case 'today':
          cutoffDate.setHours(0, 0, 0, 0);
          break;
        case 'week':
          cutoffDate.setDate(now.getDate() - 7);
          break;
        case 'month':
          cutoffDate.setMonth(now.getMonth() - 1);
          break;
        case 'season':
          cutoffDate.setMonth(7); // August (start of football season)
          if (now.getMonth() < 7) {
            cutoffDate.setFullYear(now.getFullYear() - 1);
          }
          break;
      }

      filtered = filtered.filter(t => new Date(t.createdAt) >= cutoffDate);
    }

    // Sort transactions
    filtered.sort((a, b) => {
      let aValue, bValue;

      switch (filters.sortBy) {
        case 'type':
          aValue = a.type;
          bValue = b.type;
          break;
        case 'player':
          aValue = a.playersIn?.[0]?.name || a.playersOut?.[0]?.name || '';
          bValue = b.playersIn?.[0]?.name || b.playersOut?.[0]?.name || '';
          break;
        case 'value':
          aValue = a.bidAmount || a.tradeValue || 0;
          bValue = b.bidAmount || b.tradeValue || 0;
          break;
        case 'date':
        default:
          aValue = new Date(a.createdAt).getTime();
          bValue = new Date(b.createdAt).getTime();
          break;
      }

      if (filters.sortOrder === 'asc') {
        return aValue > bValue ? 1 : -1;
      } else {
        return aValue < bValue ? 1 : -1;
      }
    });

    return filtered.slice(0, maxItems);
  }, [transactions, filters, maxItems]);

  const getTransactionIcon = (type: Transaction['type']) => {
    const icons = {
      trade: '🔄',
      waiver_claim: '📝',
      free_agent_add: '➕',
      drop: '➖',
      draft: '🎯'
    };
    return icons[type] || '📋';
  };

  const getStatusColor = (status: Transaction['status']) => {
    const colors = {
      completed: 'text-green-600 bg-green-100 border-green-200',
      pending: 'text-yellow-600 bg-yellow-100 border-yellow-200',
      rejected: 'text-red-600 bg-red-100 border-red-200'
    };
    return colors[status] || 'text-gray-600 bg-gray-100 border-gray-200';
  };

  const getTransactionDescription = (transaction: ExtendedTransaction) => {
    const { type, playersIn, playersOut, bidAmount, tradingPartner } = transaction;

    switch (type) {
      case 'trade':
        const outNames = playersOut?.map(p => p.name).join(', ') || 'Unknown';
        const inNames = playersIn?.map(p => p.name).join(', ') || 'Unknown';
        const partner = tradingPartner ? ` with ${tradingPartner.name}` : '';
        return `Traded ${outNames} for ${inNames}${partner}`;

      case 'waiver_claim':
        const waiverPlayer = playersIn?.[0]?.name || 'Unknown Player';
        const droppedPlayer = playersOut?.[0]?.name || 'No one';
        return `Claimed ${waiverPlayer} via waivers${bidAmount ? ` (Bid: $${bidAmount})` : ''}, dropped ${droppedPlayer}`;

      case 'free_agent_add':
        const addedPlayer = playersIn?.[0]?.name || 'Unknown Player';
        return `Added ${addedPlayer} from free agents`;

      case 'drop':
        const droppedName = playersOut?.[0]?.name || 'Unknown Player';
        return `Dropped ${droppedName}`;

      case 'draft':
        const draftedPlayer = playersIn?.[0]?.name || 'Unknown Player';
        const round = transaction.draftRound ? ` in Round ${transaction.draftRound}` : '';
        const pick = transaction.draftPick ? ` (Pick ${transaction.draftPick})` : '';
        return `Drafted ${draftedPlayer}${round}${pick}`;

      default:
        return 'Unknown transaction type';
    }
  };

  const toggleExpanded = (transactionId: string) => {
    setExpandedTransaction(prev => 
      prev === transactionId ? null : transactionId
    );
  };

  // Helper function to format dates consistently
  const formatDateTime = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return `${formatDate(date)} ${formatTime(date)}`;
    } catch {
      return dateString;
    }
  };

  if (loading) {
    return (
      <div className={`bg-white rounded-lg shadow-sm border border-gray-200 p-6 ${className}`}>
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-2 text-gray-600">Loading transactions...</span>
        </div>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header & Filters */}
      <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">
            {showAllLeague ? 'League' : 'Team'} Transaction History
            {filteredTransactions.length > 0 && (
              <span className="ml-2 px-2 py-1 bg-blue-100 text-blue-800 text-sm rounded-full">
                {filteredTransactions.length}
              </span>
            )}
          </h3>
          
          <div className="flex items-center space-x-2">
            {!compact && (
              <button
                onClick={() => setShowFilters(!showFilters)}
                className="text-sm text-blue-600 hover:text-blue-800 font-medium"
              >
                {showFilters ? 'Hide Filters' : 'Show Filters'}
              </button>
            )}
            <button
              onClick={fetchTransactions}
              disabled={loading}
              className="text-sm text-blue-600 hover:text-blue-800 font-medium disabled:opacity-50"
            >
              Refresh
            </button>
          </div>
        </div>
        
        {showFilters && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Transaction Type
              </label>
              <select
                value={filters.type || 'all'}
                onChange={(e) => setFilters(prev => ({
                  ...prev,
                  type: e.target.value as TransactionFilters['type']
                }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
              >
                <option value="all">All Types</option>
                <option value="draft">Draft</option>
                <option value="trade">Trade</option>
                <option value="waiver_claim">Waiver</option>
                <option value="free_agent_add">Add</option>
                <option value="drop">Drop</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Status
              </label>
              <select
                value={filters.status || 'all'}
                onChange={(e) => setFilters(prev => ({
                  ...prev,
                  status: e.target.value as TransactionFilters['status']
                }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
              >
                <option value="all">All Status</option>
                <option value="completed">Completed</option>
                <option value="pending">Pending</option>
                <option value="rejected">Rejected</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Time Period
              </label>
              <select
                value={filters.dateRange || 'season'}
                onChange={(e) => setFilters(prev => ({
                  ...prev,
                  dateRange: e.target.value as TransactionFilters['dateRange']
                }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
              >
                <option value="today">Today</option>
                <option value="week">Past Week</option>
                <option value="month">Past Month</option>
                <option value="season">This Season</option>
                <option value="all">All Time</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Search Player
              </label>
              <input
                type="text"
                placeholder="Player name..."
                value={filters.playerName || ''}
                onChange={(e) => setFilters(prev => ({
                  ...prev,
                  playerName: e.target.value
                }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
              />
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {/* Transactions List */}
      <div className="space-y-4">
        {filteredTransactions.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-lg shadow-sm border border-gray-200">
            <div className="text-gray-400 text-4xl mb-4">📋</div>
            <h3 className="text-lg font-semibold text-gray-700 mb-2">
              No Transactions Found
            </h3>
            <p className="text-gray-500">
              {filters.playerName || filters.type !== 'all' || filters.dateRange !== 'season'
                ? 'No transactions match your current filters.'
                : 'No transactions have been made yet.'
              }
            </p>
          </div>
        ) : (
          filteredTransactions.map((transaction) => {
            const isExpanded = expandedTransaction === transaction.id;
            
            return (
              <div
                key={transaction.id}
                className={`bg-white rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow ${
                  transaction.status === 'pending' ? 'border-l-4 border-l-yellow-400' :
                  transaction.status === 'rejected' ? 'border-l-4 border-l-red-400' :
                  transaction.status === 'completed' ? 'border-l-4 border-l-green-400' : ''
                }`}
              >
                <div className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start space-x-3 flex-1">
                      <div className="text-2xl flex-shrink-0">
                        {getTransactionIcon(transaction.type)}
                      </div>
                      
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2 mb-1">
                          <h4 className="font-medium text-gray-900 capitalize">
                            {transaction.type.replace('_', ' ')}
                          </h4>
                          <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getStatusColor(transaction.status)}`}>
                            {transaction.status.toUpperCase()}
                          </span>
                          {transaction.isProcessed && (
                            <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
                              PROCESSED
                            </span>
                          )}
                        </div>
                        
                        <p className="text-gray-700 mb-2">
                          {getTransactionDescription(transaction)}
                        </p>
                        
                        <div className="flex items-center justify-between text-sm text-gray-500">
                          <div className="flex items-center space-x-4">
                            <span>
                              <span className="font-medium">Date:</span>{' '}
                              {formatDate(new Date(transaction.createdAt))}
                            </span>
                            
                            {showAllLeague && transaction.teamName && (
                              <span>
                                <span className="font-medium">Team:</span>{' '}
                                {transaction.teamName}
                              </span>
                            )}
                            
                            {transaction.waiverPriority && (
                              <span>
                                <span className="font-medium">Priority:</span>{' '}
                                #{transaction.waiverPriority}
                              </span>
                            )}
                          </div>
                          
                          <div className="flex items-center space-x-2">
                            <span>{formatTime(new Date(transaction.createdAt))}</span>
                            {!compact && (
                              <button
                                onClick={() => toggleExpanded(transaction.id)}
                                className="text-blue-600 hover:text-blue-800 font-medium"
                              >
                                {isExpanded ? 'Less' : 'Details'}
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Expanded Details */}
                  {isExpanded && (
                    <div className="mt-4 pt-4 border-t border-gray-100 space-y-4">
                      {/* Player Details */}
                      {(transaction.playersIn || transaction.playersOut) && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {transaction.playersIn && transaction.playersIn.length > 0 && (
                            <div className="bg-green-50 p-3 rounded-lg">
                              <h5 className="text-sm font-medium text-green-800 mb-2">
                                Players Added ({transaction.playersIn.length})
                              </h5>
                              <div className="space-y-2">
                                {transaction.playersIn.map((player) => (
                                  <div key={player.id} className="flex items-center justify-between">
                                    <div>
                                      <div className="font-medium text-green-900">{player.name}</div>
                                      <div className="text-sm text-green-700">
                                        {player.position_short} • {player.team_short}
                                      </div>
                                    </div>
                                    <span className="text-sm text-green-700">
                                      £{(player.now_cost / 10).toFixed(1)}m
                                    </span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {transaction.playersOut && transaction.playersOut.length > 0 && (
                            <div className="bg-red-50 p-3 rounded-lg">
                              <h5 className="text-sm font-medium text-red-800 mb-2">
                                Players Removed ({transaction.playersOut.length})
                              </h5>
                              <div className="space-y-2">
                                {transaction.playersOut.map((player) => (
                                  <div key={player.id} className="flex items-center justify-between">
                                    <div>
                                      <div className="font-medium text-red-900">{player.name}</div>
                                      <div className="text-sm text-red-700">
                                        {player.position_short} • {player.team_short}
                                      </div>
                                    </div>
                                    <span className="text-sm text-red-700">
                                      £{(player.now_cost / 10).toFixed(1)}m
                                    </span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Transaction Metadata */}
                      <div className="bg-gray-50 p-3 rounded-lg">
                        <h5 className="text-sm font-medium text-gray-800 mb-2">Transaction Details</h5>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-600">
                          <div>
                            <span className="font-medium">Transaction ID:</span>{' '}
                            <span className="font-mono">{transaction.id}</span>
                          </div>
                          
                          {transaction.bidAmount && (
                            <div>
                              <span className="font-medium">Bid Amount:</span>{' '}
                              ${transaction.bidAmount}
                            </div>
                          )}
                          
                          {transaction.processedAt && (
                            <div>
                              <span className="font-medium">Processed:</span>{' '}
                              {formatDateTime(transaction.processedAt)}
                            </div>
                          )}
                          
                          {transaction.note && (
                            <div className="md:col-span-2">
                              <span className="font-medium">Note:</span>{' '}
                              {transaction.note}
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Trade Specific Details */}
                      {transaction.type === 'trade' && transaction.tradeDetails && (
                        <div className="bg-blue-50 p-3 rounded-lg">
                          <h5 className="text-sm font-medium text-blue-800 mb-2">Trade Information</h5>
                          <div className="text-sm text-blue-700 space-y-1">
                            {transaction.tradeDetails.tradeId && (
                              <div>
                                <span className="font-medium">Trade ID:</span>{' '}
                                {transaction.tradeDetails.tradeId}
                              </div>
                            )}
                            {transaction.tradingPartner && (
                              <div>
                                <span className="font-medium">Trading Partner:</span>{' '}
                                {transaction.tradingPartner.name}
                              </div>
                            )}
                            {transaction.tradeDetails.proposedAt && (
                              <div>
                                <span className="font-medium">Proposed:</span>{' '}
                                {formatDateTime(transaction.tradeDetails.proposedAt)}
                              </div>
                            )}
                            {transaction.tradeDetails.acceptedAt && (
                              <div>
                                <span className="font-medium">Accepted:</span>{' '}
                                {formatDateTime(transaction.tradeDetails.acceptedAt)}
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Summary Stats */}
      {filteredTransactions.length > 0 && !compact && (
        <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200">
          <h4 className="font-semibold mb-3">Transaction Summary</h4>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                {filteredTransactions.length}
              </div>
              <div className="text-gray-600">Total</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {filteredTransactions.filter(t => t.type === 'trade').length}
              </div>
              <div className="text-gray-600">Trades</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-yellow-600">
                {filteredTransactions.filter(t => t.type === 'waiver_claim').length}
              </div>
              <div className="text-gray-600">Waivers</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">
                {filteredTransactions.filter(t => t.type === 'draft').length}
              </div>
              <div className="text-gray-600">Draft Picks</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-orange-600">
                {filteredTransactions.filter(t => t.status === 'completed').length}
              </div>
              <div className="text-gray-600">Completed</div>
            </div>
          </div>
        </div>
      )}

      {/* Export Options */}
      {!compact && filteredTransactions.length > 0 && (
        <div className="flex justify-center space-x-2">
          <button
            onClick={() => {
              // Export as CSV
              const csvData = filteredTransactions.map(t => ({
                Date: formatDate(new Date(t.createdAt)),
                Type: t.type,
                Status: t.status,
                Description: getTransactionDescription(t),
                'Players In': t.playersIn?.map(p => p.name).join('; ') || '',
                'Players Out': t.playersOut?.map(p => p.name).join('; ') || '',
                'Bid Amount': t.bidAmount || '',
                'Trading Partner': t.tradingPartner?.name || ''
              }));
              
              const csv = [
                Object.keys(csvData[0]).join(','),
                ...csvData.map(row => Object.values(row).map(val => `"${val}"`).join(','))
              ].join('\n');
              
              const blob = new Blob([csv], { type: 'text/csv' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `transactions-${teamId}-${new Date().toISOString().split('T')[0]}.csv`;
              document.body.appendChild(a);
              a.click();
              document.body.removeChild(a);
              URL.revokeObjectURL(url);
            }}
            className="px-3 py-1 text-sm bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors"
          >
            Export CSV
          </button>
        </div>
      )}
    </div>
  );
};