// Mock data generator
const mockData = {
    companies: ['Acme Corp', 'Global Tech', 'Omega LLC', 'Apex Industries', 'Stark Enterprises', 'Wayne Corp'],

    generateTxnId: () => {
        const prefix = 'TXN';
        const random = Math.floor(Math.random() * 999999).toString().padStart(6, '0');
        return `${prefix}-${random}`;
    },

    formatCurrency: (amount) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2
        }).format(amount);
    },

    randomChoice: (arr) => {
        return arr[Math.floor(Math.random() * arr.length)];
    },

    generateTransaction: () => {
        const amount = Math.random() * 50000;
        const isFlagged = Math.random() > 0.85;

        return {
            id: mockData.generateTxnId(),
            sender: mockData.randomChoice(mockData.companies),
            receiver: mockData.randomChoice(mockData.companies),
            amount: amount,
            timestamp: new Date(),
            status: isFlagged ? 'FLAGGED' : 'CLEARED'
        };
    }
};

// Live Feed for Dashboard
const liveFeed = document.getElementById('liveFeed');

if (liveFeed) {
    const addTransaction = () => {
        const txn = mockData.generateTransaction();

        const item = document.createElement('div');
        item.className = 'feed-item';
        item.style.opacity = '0';
        item.style.transform = 'translateY(-10px)';
        item.innerHTML = `
            <span class="feed-id">${txn.id}</span>
            <span class="feed-amount">${mockData.formatCurrency(txn.amount)}</span>
            <span class="badge badge-${txn.status === 'CLEARED' ? 'success' : 'warning'}">${txn.status}</span>
        `;

        liveFeed.insertBefore(item, liveFeed.firstChild);

        // Animate in
        setTimeout(() => {
            item.style.transition = 'all 0.4s ease';
            item.style.opacity = '1';
            item.style.transform = 'translateY(0)';
        }, 100);

        // Keep only last 10
        while (liveFeed.children.length > 10) {
            liveFeed.removeChild(liveFeed.lastChild);
        }

        // Schedule next
        setTimeout(addTransaction, Math.random() * 3000 + 1000);
    };

    addTransaction();
}
