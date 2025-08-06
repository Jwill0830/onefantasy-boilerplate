/**
 * CountdownTimer component - Timer component for drafts and deadlines
 */

import React, { useState, useEffect, useCallback } from 'react';

interface CountdownTimerProps {
  targetDate?: Date;
  duration?: number; // Duration in seconds
  onComplete?: () => void;
  onTick?: (timeRemaining: number) => void;
  format?: 'full' | 'compact' | 'minimal';
  showLabels?: boolean;
  className?: string;
  urgentThreshold?: number; // Seconds at which timer becomes urgent
}

interface TimeUnits {
  days: number;
  hours: number;
  minutes: number;
  seconds: number;
}

const CountdownTimer: React.FC<CountdownTimerProps> = ({
  targetDate,
  duration,
  onComplete,
  onTick,
  format = 'full',
  showLabels = true,
  className = '',
  urgentThreshold = 60,
}) => {
  const [timeRemaining, setTimeRemaining] = useState<number>(0);
  const [isActive, setIsActive] = useState<boolean>(false);
  const [isUrgent, setIsUrgent] = useState<boolean>(false);

  // Calculate initial time remaining
  const calculateTimeRemaining = useCallback(() => {
    if (targetDate) {
      const now = new Date().getTime();
      const target = targetDate.getTime();
      return Math.max(0, Math.floor((target - now) / 1000));
    } else if (duration !== undefined) {
      return duration;
    }
    return 0;
  }, [targetDate, duration]);

  // Initialize timer
  useEffect(() => {
    const initialTime = calculateTimeRemaining();
    setTimeRemaining(initialTime);
    setIsActive(initialTime > 0);
    setIsUrgent(initialTime <= urgentThreshold);
  }, [calculateTimeRemaining, urgentThreshold]);

  // Timer logic
  useEffect(() => {
    let interval: NodeJS.Timeout | null = null;

    if (isActive && timeRemaining > 0) {
      interval = setInterval(() => {
        setTimeRemaining((prevTime) => {
          const newTime = prevTime - 1;
          
          // Check if timer should become urgent
          setIsUrgent(newTime <= urgentThreshold);
          
          // Call onTick callback
          onTick?.(newTime);
          
          // Check if timer is complete
          if (newTime <= 0) {
            setIsActive(false);
            onComplete?.();
            return 0;
          }
          
          return newTime;
        });
      }, 1000);
    } else if (interval) {
      clearInterval(interval);
    }

    return () => {
      if (interval) {
        clearInterval(interval);
      }
    };
  }, [isActive, timeRemaining, urgentThreshold, onTick, onComplete]);

  // Convert seconds to time units
  const getTimeUnits = (totalSeconds: number): TimeUnits => {
    const days = Math.floor(totalSeconds / (24 * 60 * 60));
    const hours = Math.floor((totalSeconds % (24 * 60 * 60)) / (60 * 60));
    const minutes = Math.floor((totalSeconds % (60 * 60)) / 60);
    const seconds = totalSeconds % 60;

    return { days, hours, minutes, seconds };
  };

  // Format time display based on format prop
  const formatTime = (timeUnits: TimeUnits): string => {
    const { days, hours, minutes, seconds } = timeUnits;

    switch (format) {
      case 'minimal':
        if (days > 0) return `${days}d ${hours}h`;
        if (hours > 0) return `${hours}h ${minutes}m`;
        return `${minutes}:${seconds.toString().padStart(2, '0')}`;

      case 'compact':
        if (days > 0) return `${days}d ${hours}h ${minutes}m`;
        if (hours > 0) return `${hours}h ${minutes}m ${seconds}s`;
        return `${minutes}m ${seconds}s`;

      case 'full':
      default:
        const parts: string[] = [];
        if (days > 0) parts.push(`${days} ${showLabels ? (days === 1 ? 'day' : 'days') : 'd'}`);
        if (hours > 0) parts.push(`${hours} ${showLabels ? (hours === 1 ? 'hour' : 'hours') : 'h'}`);
        if (minutes > 0) parts.push(`${minutes} ${showLabels ? (minutes === 1 ? 'minute' : 'minutes') : 'm'}`);
        if (seconds > 0 || parts.length === 0) {
          parts.push(`${seconds} ${showLabels ? (seconds === 1 ? 'second' : 'seconds') : 's'}`);
        }
        return parts.join(' ');
    }
  };

  // Get CSS classes based on timer state
  const getTimerClasses = (): string => {
    const baseClasses = 'countdown-timer';
    const urgentClass = isUrgent ? 'countdown-timer--urgent' : '';
    const inactiveClass = !isActive ? 'countdown-timer--inactive' : '';
    
    return [baseClasses, urgentClass, inactiveClass, className]
      .filter((cls): cls is string => Boolean(cls))
      .join(' ');
  };

  const timeUnits = getTimeUnits(timeRemaining);
  const formattedTime = formatTime(timeUnits);

  return (
    <div className={getTimerClasses()}>
      <div className="countdown-timer__display">
        {timeRemaining > 0 ? (
          <span className="countdown-timer__time">{formattedTime}</span>
        ) : (
          <span className="countdown-timer__complete">Time's up!</span>
        )}
      </div>
      
      {format === 'full' && timeRemaining > 0 && (
        <div className="countdown-timer__breakdown">
          {timeUnits.days > 0 && (
            <div className="countdown-timer__unit">
              <span className="countdown-timer__number">{timeUnits.days}</span>
              <span className="countdown-timer__label">{timeUnits.days === 1 ? 'Day' : 'Days'}</span>
            </div>
          )}
          {timeUnits.hours > 0 && (
            <div className="countdown-timer__unit">
              <span className="countdown-timer__number">{timeUnits.hours}</span>
              <span className="countdown-timer__label">{timeUnits.hours === 1 ? 'Hour' : 'Hours'}</span>
            </div>
          )}
          {timeUnits.minutes > 0 && (
            <div className="countdown-timer__unit">
              <span className="countdown-timer__number">{timeUnits.minutes}</span>
              <span className="countdown-timer__label">{timeUnits.minutes === 1 ? 'Minute' : 'Minutes'}</span>
            </div>
          )}
          <div className="countdown-timer__unit">
            <span className="countdown-timer__number">{timeUnits.seconds}</span>
            <span className="countdown-timer__label">{timeUnits.seconds === 1 ? 'Second' : 'Seconds'}</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default CountdownTimer;