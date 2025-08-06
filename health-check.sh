#!/bin/bash

echo "🏥 OneFantasy Health Check"
echo "========================="

if command -v lsof >/dev/null 2>&1; then
    if lsof -ti:3000 >/dev/null 2>&1; then
        echo "✅ Frontend (Port 3000) - Running"
    else
        echo "❌ Frontend (Port 3000) - Not running"
    fi
    
    if lsof -ti:5000 >/dev/null 2>&1; then
        echo "✅ Backend (Port 5000) - Running"
    else
        echo "❌ Backend (Port 5000) - Not running"
    fi
else
    echo "⚠️  Cannot check ports - lsof not available"
fi

if command -v curl >/dev/null 2>&1; then
    if curl -s --max-time 5 "http://localhost:3000" >/dev/null 2>&1; then
        echo "✅ Frontend - Responding"
    else
        echo "❌ Frontend - Not responding"
    fi
    
    if curl -s --max-time 5 "http://localhost:5000" >/dev/null 2>&1; then
        echo "✅ Backend - Responding"
    else
        echo "❌ Backend - Not responding"
    fi
fi

echo "=========================="
echo "Health check complete!"
