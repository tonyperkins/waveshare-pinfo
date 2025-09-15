// DOM Elements
const commandNameInput = document.getElementById('commandName');
const commandTypeSelect = document.getElementById('commandType');
const learnBtn = document.getElementById('learnBtn');
const commandsList = document.getElementById('commandsList');

// Sample data - in a real app, this would be stored in a database
let commands = JSON.parse(localStorage.getItem('broadlinkCommands')) || [];

// Initialize the app
function init() {
    renderCommandsList();
    setupEventListeners();
}

// Set up event listeners
function setupEventListeners() {
    learnBtn.addEventListener('click', handleLearnCommand);
}

// Handle learn command button click
function handleLearnCommand() {
    const name = commandNameInput.value.trim();
    const type = commandTypeSelect.value;
    
    if (!name) {
        showNotification('Please enter a command name', 'error');
        return;
    }
    
    // Show learning state
    const originalText = learnBtn.innerHTML;
    learnBtn.disabled = true;
    learnBtn.innerHTML = '<i class="material-icons">radio_button_checked</i> Learning...';
    learnBtn.classList.add('learning');
    
    // Simulate learning process (in a real app, this would communicate with the Broadlink device)
    setTimeout(() => {
        // Create new command
        const newCommand = {
            id: Date.now().toString(),
            name,
            type,
            code: generateRandomCode(),
            createdAt: new Date().toISOString()
        };
        
        // Add to commands array and update UI
        commands.unshift(newCommand);
        saveCommands();
        renderCommandsList();
        
        // Reset form
        commandNameInput.value = '';
        learnBtn.innerHTML = originalText;
        learnBtn.disabled = false;
        learnBtn.classList.remove('learning');
        
        // Show success message
        showNotification(`Successfully learned "${name}" command!`, 'success');
    }, 2000);
}

// Render the commands list
function renderCommandsList() {
    if (commands.length === 0) {
        commandsList.innerHTML = `
            <div class="empty-state">
                <i class="material-icons">inbox</i>
                <p>No commands learned yet</p>
            </div>
        `;
        return;
    }
    
    commandsList.innerHTML = commands.map(command => `
        <div class="command-item" data-id="${command.id}">
            <div class="command-info">
                <h3>${command.name}</h3>
                <div class="command-meta">
                    <span>${command.type.toUpperCase()}</span>
                    <span>${formatDate(command.createdAt)}</span>
                </div>
            </div>
            <div class="command-actions">
                <button class="command-btn" onclick="sendCommand('${command.id}')" title="Send">
                    <i class="material-icons">send</i>
                </button>
                <button class="command-btn" onclick="deleteCommand('${command.id}')" title="Delete">
                    <i class="material-icons">delete</i>
                </button>
            </div>
        </div>
    `).join('');
}

// Send command (simulated)
function sendCommand(id) {
    const command = commands.find(cmd => cmd.id === id);
    if (!command) return;
    
    // In a real app, this would send the command to the Broadlink device
    showNotification(`Sending "${command.name}" command...`, 'info');
    
    // Simulate sending delay
    setTimeout(() => {
        showNotification(`Command "${command.name}" sent successfully!`, 'success');
    }, 800);
}

// Delete command
function deleteCommand(id) {
    if (!confirm('Are you sure you want to delete this command?')) return;
    
    const index = commands.findIndex(cmd => cmd.id === id);
    if (index === -1) return;
    
    const commandName = commands[index].name;
    commands.splice(index, 1);
    saveCommands();
    renderCommandsList();
    
    showNotification(`Command "${commandName}" deleted`, 'info');
}

// Save commands to localStorage
function saveCommands() {
    localStorage.setItem('broadlinkCommands', JSON.stringify(commands));
}

// Show notification
function showNotification(message, type = 'info') {
    // In a real app, you might want to use a proper notification library
    console.log(`[${type.toUpperCase()}] ${message}`);
    alert(`[${type.toUpperCase()}] ${message}`);
}

// Helper: Format date
function formatDate(isoString) {
    return new Date(isoString).toLocaleString();
}

// Helper: Generate random code (simulated)
function generateRandomCode() {
    return Array.from({length: 16}, () => 
        Math.floor(Math.random() * 16).toString(16)
    ).join('');
}

// Initialize the app when the DOM is loaded
document.addEventListener('DOMContentLoaded', init);

// Make functions available globally for HTML onclick handlers
window.sendCommand = sendCommand;
window.deleteCommand = deleteCommand;
