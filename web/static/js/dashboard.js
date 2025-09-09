// Global variables
let currentData = null;
let historicalData = null;
let teamConfig = null;
let healthChart = null;
let statusChart = null;
let healthTrendsChart = null;
let statusTrendsChart = null;
let selectedStartDate = '2025-02-10'; // Default start date
let sparklineCharts = {}; // Store sparkline chart instances

// Register datalabels plugin
Chart.register(ChartDataLabels);
let trendData = null;
let visibleMembers = new Set();

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    loadDashboard();
    setupEventListeners();
    updateDateRangeDisplay(); // Initialize date range display
});

function setupEventListeners() {
    // Refresh button
    document.getElementById('refreshBtn').addEventListener('click', refreshData);
    
    // Date filter
    document.getElementById('applyDateFilter').addEventListener('click', applyDateFilter);
    
    // Date input validation
    document.getElementById('startDate').addEventListener('change', validateDate);
}

function validateDate() {
    const startDateInput = document.getElementById('startDate');
    const selectedDate = new Date(startDateInput.value);
    const minDate = new Date('2025-02-10');
    
    if (selectedDate < minDate) {
        alert('Error: Selected date cannot be earlier than February 10, 2025. Please select a valid date.');
        startDateInput.value = '2025-02-10';
        return false;
    }
    return true;
}

function applyDateFilter() {
    const startDateInput = document.getElementById('startDate');
    
    if (!validateDate()) {
        return;
    }
    
    selectedStartDate = startDateInput.value;
    
    // Update the current date range display
    updateDateRangeDisplay();
    
    // Update charts with new date range
    if (currentData && historicalData) {
        updateChartsWithDateFilter();
    }
}

function updateDateRangeDisplay() {
    const dateRangeElement = document.getElementById('currentDateRange');
    if (dateRangeElement) {
        const startDate = new Date(selectedStartDate);
        const formattedDate = startDate.toLocaleDateString('en-US', { 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric' 
        });
        dateRangeElement.textContent = `Current range: ${formattedDate} - Present`;
    }
}

function updateChartsWithDateFilter() {
    // Update sparklines
    if (currentData && currentData.team) {
        createSparklines(currentData.team);
    }
    
    // Update trend charts
    updateHealthTrendsChart();
    updateStatusTrendsChart();
}

function destroyAllSparklineCharts() {
    Object.values(sparklineCharts).forEach(chart => {
        if (chart) {
            chart.destroy();
        }
    });
    sparklineCharts = {};
}

async function loadDashboard() {
    try {
        showLoading();
        
        // Load current data
        const currentResponse = await fetch('/api/current-data');
        const currentResult = await currentResponse.json();
        
        if (currentResult.success) {
            currentData = currentResult.data;
            teamConfig = currentResult.config;
            
            // Set up team member filters
            setupTeamFilters();
            
            // Load historical data
            const historicalResponse = await fetch('/api/historical-data');
            const historicalResult = await historicalResponse.json();
            
            if (historicalResult.success) {
                historicalData = historicalResult.data;
            }
            
            // Load trend data
            const selectedMembers = Array.from(visibleMembers);
            const trendUrl = selectedMembers.length > 0 
                ? `/api/trend-data?${selectedMembers.map(m => `members=${encodeURIComponent(m)}`).join('&')}`
                : '/api/trend-data';
            const trendResponse = await fetch(trendUrl);
            const trendResult = await trendResponse.json();
            
            if (trendResult.success) {
                trendData = trendResult;
            }
            
            // Load projects at risk
            await loadProjectsAtRisk();
            
            // Load projects on hold
            await loadProjectsOnHold();
            
            // Update dashboard
            updateDashboard();
        } else {
            showError('Failed to load data: ' + currentResult.error);
        }
    } catch (error) {
        showError('Error loading dashboard: ' + error.message);
    } finally {
        hideLoading();
    }
}

async function loadProjectsAtRisk() {
    try {
        const response = await fetch('/api/projects-at-risk');
        const result = await response.json();
        
        if (result.success) {
            updateProjectsAtRiskTable(result.projects);
        } else {
            console.error('Failed to load projects at risk:', result.error);
            updateProjectsAtRiskTable([]);
        }
    } catch (error) {
        console.error('Error loading projects at risk:', error);
        updateProjectsAtRiskTable([]);
    }
}

function updateProjectsAtRiskTable(projects) {
    const tbody = document.getElementById('projectsAtRiskTableBody');
    tbody.innerHTML = '';
    
    if (projects.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="px-6 py-4 text-center text-gray-500">
                    No projects at risk found
                </td>
            </tr>
        `;
        return;
    }
    
    projects.forEach(project => {
        const row = document.createElement('tr');
        const healthClass = project.current_health === 'Off Track' ? 'text-gray-800' : 'text-gray-800';
        const healthStyle = project.current_health === 'Off Track' ? 'background-color: #FFD2CC;' : 'background-color: #FFE785;';
        
        row.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                <a href="https://hometap.atlassian.net/browse/${project.project_key}" 
                   target="_blank" 
                   class="text-blue-600 hover:text-blue-800 hover:underline">
                    ${project.project_key}
                </a>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${project.project_name}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${project.assignee}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${healthClass}" style="${healthStyle}">
                    ${project.current_health}
                </span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${project.current_status}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${project.weeks_at_risk}</td>
        `;
        
        tbody.appendChild(row);
    });
}

async function loadProjectsOnHold() {
    try {
        const response = await fetch('/api/projects-on-hold');
        const result = await response.json();
        
        if (result.success) {
            updateProjectsOnHoldTable(result.projects);
        } else {
            console.error('Failed to load projects on hold:', result.error);
            updateProjectsOnHoldTable([]);
        }
    } catch (error) {
        console.error('Error loading projects on hold:', error);
        updateProjectsOnHoldTable([]);
    }
}

function updateProjectsOnHoldTable(projects) {
    const tbody = document.getElementById('projectsOnHoldTableBody');
    tbody.innerHTML = '';
    
    if (projects.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="px-6 py-4 text-center text-gray-500">
                    No projects on hold found
                </td>
            </tr>
        `;
        return;
    }
    
    projects.forEach(project => {
        const row = document.createElement('tr');
        const healthClass = 'text-gray-800';
        const healthStyle = 'background-color: #F3F0FF;';
        
        row.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                <a href="https://hometap.atlassian.net/browse/${project.project_key}" 
                   target="_blank" 
                   class="text-blue-600 hover:text-blue-800 hover:underline">
                    ${project.project_key}
                </a>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${project.project_name}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${project.assignee}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${healthClass}" style="${healthStyle}">
                    ${project.current_health}
                </span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${project.current_status}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${project.weeks_on_hold}</td>
        `;
        
        tbody.appendChild(row);
    });
}

function setupTeamFilters() {
    const filterContainer = document.getElementById('teamFilter');
    filterContainer.innerHTML = '';
    
    // Initialize visible members with default
    visibleMembers = new Set(teamConfig.default_visible);
    
    teamConfig.team_members.forEach(member => {
        const checkbox = document.createElement('div');
        checkbox.className = 'flex items-center';
        checkbox.innerHTML = `
            <input type="checkbox" id="filter-${member}" class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded" 
                   ${visibleMembers.has(member) ? 'checked' : ''}>
            <label for="filter-${member}" class="ml-2 text-sm text-gray-700">${member}</label>
        `;
        
        checkbox.querySelector('input').addEventListener('change', async function() {
            if (this.checked) {
                visibleMembers.add(member);
            } else {
                visibleMembers.delete(member);
            }
            await updateDashboard();
        });
        
        filterContainer.appendChild(checkbox);
    });
}

async function updateDashboard() {
    if (!currentData || !teamConfig) return;
    
    // Reload trend data with current filters
    const selectedMembers = Array.from(visibleMembers);
    const trendUrl = selectedMembers.length > 0 
        ? `/api/trend-data?${selectedMembers.map(m => `members=${encodeURIComponent(m)}`).join('&')}`
        : '/api/trend-data';
    const trendResponse = await fetch(trendUrl);
    const trendResult = await trendResponse.json();
    
    if (trendResult.success) {
        trendData = trendResult;
    }
    
    updateSummaryCards();
    updateTeamTable();
    updateCharts();
}

function updateSummaryCards() {
    const teamData = currentData.team;
    const healthData = currentData.health;
    
    // Filter to visible members
    const visibleTeamData = teamData.filter(member => visibleMembers.has(member.team_member));
    
    // Active team members
    document.getElementById('activeMembers').textContent = visibleTeamData.length;
    
    // Health counts
    const healthCounts = {};
    healthData.forEach(item => {
        healthCounts[item.health_status] = item.count;
    });
    
    document.getElementById('onTrackCount').textContent = healthCounts['On Track'] || 0;
    document.getElementById('atRiskCount').textContent = healthCounts['At Risk'] || 0;
    
    // Overloaded count (projects > threshold)
    const overloaded = visibleTeamData.filter(member => member.total_issues > teamConfig.alert_threshold).length;
    document.getElementById('overloadedCount').textContent = overloaded;
    
    // Last updated
    if (teamData.length > 0) {
        document.getElementById('lastUpdated').textContent = teamData[0].date || 'Unknown';
    }
}

function updateTeamTable() {
    const tbody = document.getElementById('teamTableBody');
    tbody.innerHTML = '';
    
    const teamData = currentData.team.filter(member => visibleMembers.has(member.team_member));
    
    // Sort by total issues (descending)
    teamData.sort((a, b) => b.total_issues - a.total_issues);
    
    teamData.forEach(member => {
        const row = document.createElement('tr');
        const isOverloaded = member.total_issues > teamConfig.alert_threshold;
        const rowClass = isOverloaded ? 'bg-red-50' : '';
        
        row.className = rowClass;
        row.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                ${member.team_member}
                ${isOverloaded ? '<span class="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">Overloaded</span>' : ''}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${member.total_issues}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${member.weighted_capacity || 'N/A'}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                <div class="flex flex-wrap gap-1">
                    ${member.on_track ? `<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium text-gray-800" style="background-color: #AFF3D6;">${member.on_track} On Track</span>` : ''}
                    ${member.off_track ? `<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium text-gray-800" style="background-color: #FFD2CC;">${member.off_track} Off Track</span>` : ''}
                    ${member.at_risk ? `<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium text-gray-800" style="background-color: #FFE785;">${member.at_risk} At Risk</span>` : ''}
                    ${member.complete ? `<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium text-white" style="background-color: #0C66E4;">${member.complete} Complete</span>` : ''}
                    ${member.on_hold ? `<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium text-gray-800" style="background-color: #F3F0FF;">${member.on_hold} On Hold</span>` : ''}
                    ${member.mystery ? `<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium text-white" style="background-color: #6E5DC6;">${member.mystery} Mystery</span>` : ''}
                    ${member.unknown_health ? `<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-200 text-gray-600">${member.unknown_health} Unknown</span>` : ''}
                </div>
            </td>
            <td class="px-6 py-6 whitespace-nowrap text-sm text-gray-900">
                <canvas id="sparkline-${member.team_member}" width="100" height="50"></canvas>
            </td>
        `;
        
        tbody.appendChild(row);
    });
    
    // Create sparklines after DOM update
    setTimeout(() => {
        createSparklines(teamData);
    }, 100);
}

function createSparklines(teamData) {
    const startDate = new Date(selectedStartDate);
    
    // Create a complete weekly date range from start date to present
    const completeDateRange = [];
    const currentDate = new Date();
    const tempDate = new Date(startDate);
    
    while (tempDate <= currentDate) {
        completeDateRange.push(new Date(tempDate));
        tempDate.setDate(tempDate.getDate() + 7); // Weekly intervals
    }
    
    // Define when each team member actually started having projects
    const teamMemberStartDates = {
        'Adam Sigel': new Date('2025-02-10'),
        'Jennie Goldenberg': new Date('2025-02-10'),
        'Jacqueline Gallagher': new Date('2025-02-10'),
        'Robert J. Johnson': new Date('2025-02-10'),
        'Garima Giri': new Date('2025-02-24'),
        'Lizzy Magill': new Date('2025-03-24'),
        'Sanela Smaka': new Date('2025-04-28')
    };
    
    // Calculate maxValue across all normalized data for consistent y-axis scaling
    let maxValue = 0;
    
    teamData.forEach(member => {
        if (historicalData && historicalData.team) {
            const memberHistory = historicalData.team.filter(h => 
                h.team_member === member.team_member && 
                new Date(h.date) >= startDate
            );
            
            // Create normalized data for this member
            const memberStartDate = teamMemberStartDates[member.team_member] || startDate;
            const normalizedData = completeDateRange.map(date => {
                // If date is before team member started, return 0
                if (date < memberStartDate) {
                    return 0;
                }
                
                // Find actual data for this specific date
                const weekData = memberHistory.find(h => {
                    const dataDate = new Date(h.date);
                    // Compare dates by year, month, day only (ignore time)
                    return dataDate.getFullYear() === date.getFullYear() &&
                           dataDate.getMonth() === date.getMonth() &&
                           dataDate.getDate() === date.getDate();
                });
                return weekData ? weekData.total_issues : 0;
            });
            
            // Update maxValue
            const memberMax = Math.max(...normalizedData);
            maxValue = Math.max(maxValue, memberMax);
        }
    });
    
    teamData.forEach(member => {
        const canvasId = `sparkline-${member.team_member}`;
        const canvas = document.getElementById(canvasId);
        
        if (canvas && historicalData && historicalData.team) {
            // Destroy existing chart if it exists
            if (sparklineCharts[member.team_member]) {
                sparklineCharts[member.team_member].destroy();
                delete sparklineCharts[member.team_member];
            }
            
            // Get historical data for this member, filtered by start date
            const memberHistory = historicalData.team.filter(h => 
                h.team_member === member.team_member && 
                new Date(h.date) >= startDate
            );
            
            // Create normalized data for this member
            const memberStartDate = teamMemberStartDates[member.team_member] || startDate;
            const normalizedData = completeDateRange.map(date => {
                // If date is before team member started, return 0
                if (date < memberStartDate) {
                    return 0;
                }
                
                // Find actual data for this specific date
                const weekData = memberHistory.find(h => {
                    const dataDate = new Date(h.date);
                    // Compare dates by year, month, day only (ignore time)
                    return dataDate.getFullYear() === date.getFullYear() &&
                           dataDate.getMonth() === date.getMonth() &&
                           dataDate.getDate() === date.getDate();
                });
                return weekData ? weekData.total_issues : 0;
            });
            
            if (normalizedData.some(value => value > 0)) {
                const ctx = canvas.getContext('2d');
                const data = normalizedData;
                const dates = completeDateRange;
                
                sparklineCharts[member.team_member] = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: dates,
                        datasets: [{
                            data: data,
                            borderColor: '#3B82F6',
                            backgroundColor: 'rgba(59, 130, 246, 0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.4,
                            pointRadius: 0,
                            pointHoverRadius: 6
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: false },
                            datalabels: {
                                display: false
                            },
                            tooltip: {
                                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                                titleColor: '#ffffff',
                                bodyColor: '#ffffff',
                                borderColor: '#3B82F6',
                                borderWidth: 1,
                                cornerRadius: 6,
                                displayColors: false,
                                callbacks: {
                                    title: function(context) {
                                        const date = new Date(context[0].label);
                                        return date.toLocaleDateString('en-US', { 
                                            month: 'short', 
                                            day: 'numeric', 
                                            year: 'numeric' 
                                        });
                                    },
                                    label: function(context) {
                                        return `${context.parsed.y} projects`;
                                    }
                                }
                            }
                        },
                        scales: {
                            x: { display: false },
                            y: { 
                                display: false,
                                min: 0,
                                max: maxValue
                            }
                        },
                        interaction: {
                            intersect: false
                        }
                    }
                });
            }
        }
    });
}

function updateCharts() {
    updateHealthChart();
    updateStatusChart();
    updateHealthTrendsChart();
    updateStatusTrendsChart();
}

function updateHealthChart() {
    const ctx = document.getElementById('healthChart').getContext('2d');
    
    if (healthChart) {
        healthChart.destroy();
    }
    
    const healthData = currentData.health;
    const labels = healthData.map(h => h.health_status);
    const counts = healthData.map(h => h.count);
    
    const colors = {
        'On Track': '#AFF3D6',
        'Off Track': '#FFD2CC',
        'At Risk': '#FFE785',
        'Complete': '#0C66E4',
        'On Hold': '#F3F0FF',
        'Mystery': '#6E5DC6',
        'Unknown': 'rgba(156, 163, 175, 0.8)'
    };
    
    healthChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: counts,
                backgroundColor: labels.map(label => colors[label] || 'rgba(156, 163, 175, 0.8)'),
                borderWidth: 2,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                },
                datalabels: {
                    display: true,
                    color: '#ffffff',
                    font: {
                        weight: 'bold',
                        size: 12
                    },
                    formatter: (value, context) => {
                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                        const percentage = ((value / total) * 100).toFixed(0);
                        return value > 0 ? `${value}\n(${percentage}%)` : '';
                    }
                }
            }
        },
        plugins: [{
            id: 'datalabels',
            afterDatasetsDraw: (chart) => {
                // Disabled to prevent competing labels
            }
        }]
    });
}

function updateStatusChart() {
    const ctx = document.getElementById('statusChart').getContext('2d');
    
    if (statusChart) {
        statusChart.destroy();
    }
    
    const statusData = currentData.status;
    const labels = statusData.map(s => s.project_status);
    const counts = statusData.map(s => s.count);
    
    const colors = {
        '02 Generative Discovery': 'rgba(59, 130, 246, 0.8)',
        '04 Problem Discovery': 'rgba(16, 185, 129, 0.8)',
        '05 Solution Discovery': 'rgba(245, 158, 11, 0.8)',
        '06 Build': 'rgba(239, 68, 68, 0.8)',
        '07 Beta': 'rgba(139, 92, 246, 0.8)',
        'Unknown': 'rgba(107, 114, 128, 0.8)'
    };
    
    statusChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: counts,
                backgroundColor: labels.map(label => colors[label] || 'rgba(156, 163, 175, 0.8)'),
                borderWidth: 2,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                },
                datalabels: {
                    display: true,
                    color: '#ffffff',
                    font: {
                        weight: 'bold',
                        size: 12
                    },
                    formatter: (value, context) => {
                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                        const percentage = ((value / total) * 100).toFixed(0);
                        return value > 0 ? `${value}\n(${percentage}%)` : '';
                    }
                }
            }
        },
        plugins: [{
            id: 'datalabels',
            afterDatasetsDraw: (chart) => {
                // Disabled to prevent competing labels
            }
        }]
    });
}

function updateHealthTrendsChart() {
    const ctx = document.getElementById('healthTrendsChart').getContext('2d');
    
    if (healthTrendsChart) {
        healthTrendsChart.destroy();
    }
    
    if (!trendData || !trendData.health_trends) {
        return;
    }
    
    const startDate = new Date(selectedStartDate);
    const healthTrends = trendData.health_trends.filter(t => new Date(t.date) >= startDate);
    const dates = healthTrends.map(t => new Date(t.date));
    
    const healthStatuses = ['On Track', 'Off Track', 'At Risk', 'Complete', 'On Hold', 'Mystery', 'Unknown'];
    const colors = {
        'On Track': '#AFF3D6',
        'Off Track': '#FFD2CC',
        'At Risk': '#FFE785',
        'Complete': '#0C66E4',
        'On Hold': '#F3F0FF',
        'Mystery': '#6E5DC6',
        'Unknown': 'rgba(156, 163, 175, 0.8)'
    };
    
    const datasets = healthStatuses.map(status => ({
        label: status,
        data: healthTrends.map(t => t[status] || 0),
        backgroundColor: colors[status],
        borderColor: colors[status].replace('0.8', '1'),
        borderWidth: 1
    }));
    
    healthTrendsChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: dates,
            datasets: datasets
        },
        options: {
            responsive: true,
            scales: {
                x: {
                    stacked: true,
                    type: 'time',
                    time: {
                        unit: 'week'
                    },
                    title: {
                        display: true,
                        text: 'Date'
                    }
                },
                y: {
                    stacked: true,
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Number of Projects'
                    }
                }
            },
            plugins: {
                legend: {
                    position: 'top'
                },
                datalabels: {
                    display: function(context) {
                        // Only show total on the top segment of each bar
                        return context.datasetIndex === 0;
                    },
                    color: '#000',
                    font: {
                        weight: 'bold',
                        size: 12
                    },
                    formatter: function(value, context) {
                        // Calculate total for this bar
                        const dataIndex = context.dataIndex;
                        const total = context.chart.data.datasets.reduce((sum, dataset) => sum + (dataset.data[dataIndex] || 0), 0);
                        return total > 0 ? total : '';
                    },
                    anchor: 'end',
                    align: 'end',
                    offset: 10
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#ffffff',
                    bodyColor: '#ffffff',
                    borderColor: '#3B82F6',
                    borderWidth: 1,
                    cornerRadius: 6,
                    callbacks: {
                        title: function(context) {
                            const date = new Date(context[0].label);
                            return date.toLocaleDateString('en-US', { 
                                month: 'short', 
                                day: 'numeric', 
                                year: 'numeric' 
                            });
                        },
                        label: function(context) {
                            return `${context.dataset.label}: ${context.parsed.y} projects`;
                        }
                    }
                }
            }
        }
    });
}

function updateStatusTrendsChart() {
    const canvas = document.getElementById('statusTrendsChart');
    if (!canvas) {
        console.error('Status trends chart canvas not found');
        return;
    }
    
    const ctx = canvas.getContext('2d');
    
    if (statusTrendsChart) {
        statusTrendsChart.destroy();
    }
    
    if (!trendData || !trendData.status_trends) {
        console.error('Status trends data not available');
        return;
    }
    
    const startDate = new Date(selectedStartDate);
    const statusTrends = trendData.status_trends.filter(t => new Date(t.date) >= startDate);
    const dates = statusTrends.map(t => new Date(t.date));
    
    const projectStatuses = ['Generative Discovery', 'Problem Discovery', 'Solution Discovery', 'Build', 'Beta', 'Unknown'];
    const colors = {
        'Generative Discovery': 'rgba(59, 130, 246, 0.8)',
        'Problem Discovery': 'rgba(16, 185, 129, 0.8)',
        'Solution Discovery': 'rgba(245, 158, 11, 0.8)',
        'Build': 'rgba(239, 68, 68, 0.8)',
        'Beta': 'rgba(139, 92, 246, 0.8)',
        'Unknown': 'rgba(107, 114, 128, 0.8)'
    };
    
    const datasets = projectStatuses.map(status => ({
        label: status,
        data: statusTrends.map(t => t[status] || 0),
        backgroundColor: colors[status],
        borderColor: colors[status].replace('0.8', '1'),
        borderWidth: 1
    }));
    
    try {
        statusTrendsChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: dates,
                datasets: datasets
            },
            options: {
                responsive: true,
                scales: {
                    x: {
                        stacked: true,
                        type: 'time',
                        time: {
                            unit: 'week'
                        },
                        title: {
                            display: true,
                            text: 'Date'
                        }
                    },
                    y: {
                        stacked: true,
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Number of Projects'
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top'
                    },
                    datalabels: {
                        display: function(context) {
                            // Only show total on the top segment of each bar
                            return context.datasetIndex === 0;
                        },
                        color: '#000',
                        font: {
                            weight: 'bold',
                            size: 12
                        },
                        formatter: function(value, context) {
                            // Calculate total for this bar
                            const dataIndex = context.dataIndex;
                            const total = context.chart.data.datasets.reduce((sum, dataset) => sum + (dataset.data[dataIndex] || 0), 0);
                            return total > 0 ? total : '';
                        },
                        anchor: 'end',
                        align: 'end',
                        offset: 10
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#ffffff',
                        bodyColor: '#ffffff',
                        borderColor: '#3B82F6',
                        borderWidth: 1,
                        cornerRadius: 6,
                        callbacks: {
                            title: function(context) {
                                const date = new Date(context[0].label);
                                return date.toLocaleDateString('en-US', { 
                                    month: 'short', 
                                    day: 'numeric', 
                                    year: 'numeric' 
                                });
                            },
                            label: function(context) {
                                return `${context.dataset.label}: ${context.parsed.y} projects`;
                            }
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error creating status trends chart:', error);
    }
}

async function refreshData() {
    try {
        showLoading();
        
        const response = await fetch('/api/refresh-data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Reload dashboard after successful refresh
            await loadDashboard();
            showSuccess('Data refreshed successfully!');
        } else {
            showError('Failed to refresh data: ' + result.error);
        }
    } catch (error) {
        showError('Error refreshing data: ' + error.message);
    } finally {
        hideLoading();
    }
}

function showLoading() {
    document.getElementById('loadingOverlay').classList.remove('hidden');
}

function hideLoading() {
    document.getElementById('loadingOverlay').classList.add('hidden');
}

function showError(message) {
    // Simple error display - you could enhance this with a proper notification system
    alert('Error: ' + message);
}

function showSuccess(message) {
    // Simple success display - you could enhance this with a proper notification system
    alert('Success: ' + message);
}
