// student/static/js/email_templates.js

const EmailTemplates = {
    /**
     * Generate OTP verification email HTML
     * @param {Object} data - Registration data
     * @param {string} otp - One-time password
     * @returns {string} HTML email content
     */
    generateOTPEmail: function(data, otp) {
        return `
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
            </style>
        </head>
        <body style="margin:0; padding:0; font-family: 'Inter', 'Segoe UI', Arial, sans-serif; background-color: #f0f4f8;">
            <!-- Main Container -->
            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f0f4f8; padding: 40px 20px;">
                <tr>
                    <td align="center">
                        <!-- Email Card -->
                        <table width="560" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 24px; box-shadow: 0 20px 40px rgba(0,0,0,0.08); overflow: hidden; border: 1px solid #e9ecef;">
                            
                            <!-- Header with Gradient - NO LOGO -->
                            <tr>
                                <td style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
                                    <h1 style="color: white; margin: 0; font-size: 24px; font-weight: 600;">Cebu Technological University</h1>
                                    <p style="color: rgba(255,255,255,0.9); margin: 8px 0 0; font-size: 14px;">Moalboal Campus</p>
                                </td>
                            </tr>
                            
                            <!-- Greeting -->
                            <tr>
                                <td style="padding: 40px 30px 20px;">
                                    <h2 style="color: #1a2639; margin: 0 0 10px; font-size: 22px; font-weight: 600;">Hello, <span style="color: #667eea;">${data.first_name} ${data.last_name}</span>!</h2>
                                    <p style="color: #4a5568; margin: 0; font-size: 15px; line-height: 1.6;">Thank you for registering with CTU Moalboal Campus. Please verify your email address to complete your registration.</p>
                                </td>
                            </tr>
                            
                            <!-- OTP Box -->
                            <tr>
                                <td style="padding: 10px 30px;">
                                    <table width="100%" cellpadding="0" cellspacing="0" style="background: linear-gradient(135deg, #f8faff 0%, #f0f4ff 100%); border-radius: 16px; border: 1px solid #e0e7ff; padding: 25px;">
                                        <tr>
                                            <td align="center">
                                                <p style="color: #4a5568; margin: 0 0 10px; font-size: 14px; font-weight: 500; text-transform: uppercase; letter-spacing: 1px;">Your Verification Code</p>
                                                <div style="background: white; padding: 20px 30px; border-radius: 12px; display: inline-block; box-shadow: 0 4px 6px rgba(102, 126, 234, 0.1); border: 1px solid #d0d9ff;">
                                                    <span style="font-size: 42px; font-weight: 700; letter-spacing: 8px; color: #1a2639; font-family: 'Courier New', monospace;">${otp}</span>
                                                </div>
                                                <p style="color: #718096; margin: 15px 0 0; font-size: 13px;">This code will expire in <strong style="color: #667eea;">10 minutes</strong></p>
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>
                            
                            <!-- Registration Details -->
                            <tr>
                                <td style="padding: 30px 30px 20px;">
                                    <h3 style="color: #1a2639; margin: 0 0 15px; font-size: 16px; font-weight: 600; border-bottom: 2px solid #e9ecef; padding-bottom: 10px;">📋 Registration Summary</h3>
                                    <table width="100%" cellpadding="0" cellspacing="0">
                                        <tr>
                                            <td width="50%" style="padding: 5px 0;">
                                                <p style="color: #718096; margin: 0; font-size: 13px;">Program Type</p>
                                                <p style="color: #1a2639; margin: 3px 0; font-size: 15px; font-weight: 500;">${data.program_type_name || 'Not specified'}</p>
                                            </td>
                                            <td width="50%" style="padding: 5px 0;">
                                                <p style="color: #718096; margin: 0; font-size: 13px;">Year Level</p>
                                                <p style="color: #1a2639; margin: 3px 0; font-size: 15px; font-weight: 500;">${data.year_level}</p>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td colspan="2" style="padding: 5px 0;">
                                                <p style="color: #718096; margin: 0; font-size: 13px;">Course</p>
                                                <p style="color: #1a2639; margin: 3px 0; font-size: 15px; font-weight: 500;">${data.course_name}</p>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td colspan="2" style="padding: 5px 0;">
                                                <p style="color: #718096; margin: 0; font-size: 13px;">Student ID</p>
                                                <p style="color: #1a2639; margin: 3px 0; font-size: 15px; font-weight: 500; font-family: 'Courier New', monospace;">${data.id_number}</p>
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>
                            
                            <!-- Important Notes -->
                            <tr>
                                <td style="padding: 0 30px;">
                                    <table width="100%" cellpadding="0" cellspacing="0" style="background: #fef9e7; border-radius: 12px; border-left: 4px solid #fbbf24; padding: 15px;">
                                        <tr>
                                            <td style="padding-right: 10px; width: 30px;">
                                                <span style="font-size: 20px;">⚠️</span>
                                            </td>
                                            <td>
                                                <p style="color: #92400e; margin: 0; font-size: 13px; line-height: 1.5;">For security reasons, never share this OTP with anyone. CTU will never ask for your password or verification code via phone or email.</p>
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>
                            
                            <!-- Footer -->
                            <tr>
                                <td style="padding: 40px 30px 30px; border-top: 1px solid #e9ecef; margin-top: 20px;">
                                    <p style="color: #94a3b8; margin: 0 0 10px; font-size: 12px; text-align: center;">This is an automated message from CTU Moalboal Campus Student Portal</p>
                                    <p style="color: #94a3b8; margin: 0; font-size: 12px; text-align: center;">© 2024 Cebu Technological University Moalboal Campus. All rights reserved.</p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        `;
    },

    /**
     * Generate Resend OTP email HTML
     * @param {Object} data - Registration data
     * @param {string} otp - One-time password
     * @returns {string} HTML email content
     */
    generateResendOTPEmail: function(data, otp) {
        return `
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
            </style>
        </head>
        <body style="margin:0; padding:0; font-family: 'Inter', 'Segoe UI', Arial, sans-serif; background-color: #f0f4f8;">
            <!-- Main Container -->
            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f0f4f8; padding: 40px 20px;">
                <tr>
                    <td align="center">
                        <!-- Email Card -->
                        <table width="560" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 24px; box-shadow: 0 20px 40px rgba(0,0,0,0.08); overflow: hidden; border: 1px solid #e9ecef;">
                            
                            <!-- Header - NO LOGO -->
                            <tr>
                                <td style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); padding: 30px; text-align: center;">
                                    <h1 style="color: white; margin: 0; font-size: 24px; font-weight: 600;">Cebu Technological University</h1>
                                    <p style="color: rgba(255,255,255,0.9); margin: 8px 0 0; font-size: 14px;">Moalboal Campus</p>
                                    <div style="margin-top: 15px;">
                                        <span style="color: white; font-size: 16px; background: rgba(255,255,255,0.2); padding: 5px 15px; border-radius: 20px;">New Verification Code</span>
                                    </div>
                                </td>
                            </tr>
                            
                            <!-- Body -->
                            <tr>
                                <td style="padding: 40px 30px;">
                                    <p style="color: #4a5568; margin: 0 0 20px; font-size: 16px;">Hello <strong style="color: #f59e0b;">${data.first_name}</strong>,</p>
                                    <p style="color: #4a5568; margin: 0 0 25px; font-size: 15px; line-height: 1.6;">You requested a new verification code. Use the code below to complete your registration:</p>
                                    
                                    <div style="background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); border-radius: 16px; padding: 30px; text-align: center; border: 1px solid #fbbf24;">
                                        <span style="font-size: 48px; font-weight: 700; letter-spacing: 8px; color: #92400e; font-family: 'Courier New', monospace;">${otp}</span>
                                        <p style="color: #92400e; margin: 15px 0 0; font-size: 14px;">⏰ This code expires in 10 minutes</p>
                                    </div>
                                    
                                    <p style="color: #718096; margin: 25px 0 0; font-size: 13px; font-style: italic;">If you didn't request this, please ignore this email or contact support.</p>
                                </td>
                            </tr>
                            
                            <!-- Footer -->
                            <tr>
                                <td style="padding: 30px; border-top: 1px solid #e9ecef; background: #f8fafc;">
                                    <p style="color: #94a3b8; margin: 0; font-size: 12px; text-align: center;">CTU Moalboal Campus Student Portal</p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        `;
    }
};

// Make it available globally
if (typeof module !== 'undefined' && module.exports) {
    module.exports = EmailTemplates;
}