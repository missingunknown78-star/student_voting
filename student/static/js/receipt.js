// static/js/receipt.js

// Toggle receipt expansion
function toggleReceipt(voteId) {
    const receiptCard = document.getElementById('receipt-' + voteId);
    
    // Check if this card is expanded
    if (receiptCard.classList.contains('expanded')) {
        receiptCard.classList.remove('expanded');
    } else {
        // Close all other receipts first
        document.querySelectorAll('.receipt-card').forEach(card => {
            card.classList.remove('expanded');
        });
        // Open this one
        receiptCard.classList.add('expanded');
    }
}

// Download receipt as PDF
function downloadReceiptAsPDF(voteId) {
    const receiptCard = document.getElementById('receipt-' + voteId);
    
    // Get receipt details
    const title = receiptCard.querySelector('.receipt-header-title').textContent;
    const dateElement = receiptCard.querySelector('.receipt-header-date');
    const fullDate = dateElement ? dateElement.textContent.trim() : 'Date not available';
    const dateStr = fullDate.replace('📅', '').trim();
    
    const secretCode = receiptCard.querySelector('.secret-code').textContent;
    
    // Get all detail rows
    const details = [];
    const detailRows = receiptCard.querySelectorAll('.detail-row');
    detailRows.forEach(row => {
        const label = row.querySelector('.detail-label').textContent;
        const value = row.querySelector('.detail-value').textContent;
        if (!label.includes('Status')) {
            details.push({ label, value });
        }
    });
    
    // Get current date and time
    const now = new Date();
    const timeStr = now.toLocaleTimeString();
    const dateTimeStr = now.toLocaleString();
    
    // Create PDF using jsPDF
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF({
        orientation: 'portrait',
        unit: 'mm',
        format: [80, 140] // Receipt size: 80mm width
    });
    
    // Set font
    doc.setFont('courier', 'normal');
    
    // Header
    doc.setFontSize(14);
    doc.setFont('courier', 'bold');
    doc.setTextColor(0, 0, 0);
    doc.text('CTU - MOALBOAL', 40, 10, { align: 'center' });
    
    doc.setFontSize(16);
    doc.text('VOTING RECEIPT', 40, 18, { align: 'center' });
    
    doc.setFontSize(8);
    doc.setFont('courier', 'normal');
    doc.text('STUDENT GOVERNMENT ELECTIONS', 40, 24, { align: 'center' });
    
    // Dashed line
    doc.setDrawColor(0, 0, 0);
    doc.setLineWidth(0.3);
    doc.line(5, 27, 75, 27);
    
    // Election Info
    let yPos = 32;
    doc.setFontSize(9);
    doc.setFont('courier', 'bold');
    doc.text('ELECTION:', 8, yPos);
    doc.setFont('courier', 'normal');
    doc.text(title, 45, yPos);
    
    yPos += 5;
    doc.setFont('courier', 'bold');
    doc.text('DATE:', 8, yPos);
    doc.setFont('courier', 'normal');
    doc.text(dateStr, 45, yPos);
    
    yPos += 5;
    doc.setFont('courier', 'bold');
    doc.text('TIME:', 8, yPos);
    doc.setFont('courier', 'normal');
    doc.text(timeStr, 45, yPos);
    
    yPos += 5;
    doc.setFont('courier', 'bold');
    doc.text('TXN ID:', 8, yPos);
    doc.setFont('courier', 'normal');
    doc.text('#' + voteId, 45, yPos);
    
    yPos += 8;
    
    // Secret Code Box
    doc.setFillColor(240, 240, 240);
    doc.rect(8, yPos, 64, 18, 'F');
    doc.setDrawColor(0, 0, 0);
    doc.setLineWidth(0.5);
    doc.rect(8, yPos, 64, 18, 'S');
    
    doc.setFontSize(8);
    doc.setFont('courier', 'bold');
    doc.text('VERIFICATION CODE', 40, yPos + 5, { align: 'center' });
    
    doc.setFontSize(14);
    doc.setFont('courier', 'bold');
    doc.setTextColor(0, 0, 0);
    doc.text(secretCode, 40, yPos + 14, { align: 'center' });
    
    yPos += 22;
    
    // Vote Details Header
    doc.setFontSize(10);
    doc.setFont('courier', 'bold');
    doc.text('VOTE DETAILS', 40, yPos, { align: 'center' });
    
    yPos += 2;
    doc.line(5, yPos, 75, yPos);
    yPos += 4;
    
    // Vote Details
    doc.setFontSize(9);
    details.forEach(detail => {
        doc.setFont('courier', 'bold');
        doc.text(detail.label + ':', 8, yPos);
        
        // Handle long values
        let value = detail.value;
        if (value.length > 15) {
            value = value.substring(0, 15) + '...';
        }
        
        doc.setFont('courier', 'normal');
        doc.text(value, 70, yPos, { align: 'right' });
        yPos += 5;
    });
    
    yPos += 2;
    
    // Status
    doc.setFont('courier', 'bold');
    doc.setTextColor(5, 150, 105);
    doc.text('✓ RECORDED ON BLOCKCHAIN', 40, yPos, { align: 'center' });
    
    yPos += 8;
    
    // Dashed line
    doc.setDrawColor(0, 0, 0);
    doc.setLineDashPattern([2, 2], 0);
    doc.line(5, yPos, 75, yPos);
    doc.setLineDashPattern([], 0);
    
    yPos += 6;
    
    // Footer
    doc.setFontSize(8);
    doc.setTextColor(100, 100, 100);
    doc.setFont('courier', 'normal');
    doc.text('TRANSACTION #' + voteId, 40, yPos, { align: 'center' });
    
    yPos += 4;
    doc.setFontSize(7);
    doc.text(dateTimeStr, 40, yPos, { align: 'center' });
    
    yPos += 6;
    doc.setFontSize(10);
    doc.setFont('courier', 'bold');
    doc.setTextColor(0, 0, 0);
    doc.text('THANK YOU FOR VOTING!', 40, yPos, { align: 'center' });
    
    yPos += 5;
    doc.setFontSize(8);
    doc.setFont('courier', 'normal');
    doc.text('✧ ✧ ✧ ✧ ✧ ✧ ✧ ✧ ✧ ✧', 40, yPos, { align: 'center' });
    
    yPos += 5;
    doc.setFontSize(6);
    doc.setTextColor(200, 0, 0);
    doc.text('CODE CANNOT BE RECOVERED IF LOST', 40, yPos, { align: 'center' });
    
    // Cut line at bottom
    yPos += 5;
    doc.setDrawColor(150, 150, 150);
    doc.setLineDashPattern([1, 1], 0);
    doc.line(5, yPos, 75, yPos);
    doc.setFontSize(6);
    doc.setTextColor(150, 150, 150);
    doc.text('- - - - - CUT HERE - - - - -', 40, yPos + 3, { align: 'center' });
    
    // Save the PDF
    doc.save(`voting-receipt-${voteId}.pdf`);
}

// Auto-expand first receipt on page load
document.addEventListener('DOMContentLoaded', function() {
    const receipts = document.querySelectorAll('.receipt-card');
    if (receipts.length > 0) {
        receipts[0].classList.add('expanded');
    }
    console.log('Receipt page loaded with ' + receipts.length + ' receipts');
});