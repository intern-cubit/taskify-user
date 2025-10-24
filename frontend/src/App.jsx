import React, { useEffect, useState } from 'react'
import { ThemeProvider } from './contexts/ThemeContext'
import Dashboard from './pages/Dashboard'
import './index.css' // Assuming you have a basic CSS file for Tailwind or global styles
import { Info } from 'lucide-react';
import SystemActivation from './pages/SystemActivation';
import Header from './components/Header';

export default function App() {
    const [isActivated, setIsActivated] = useState(null);
    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

    useEffect(() => {
        const checkActivation = async () => {
            try {
                console.log("Checking activation status...");
                const response = await fetch('http://localhost:8000/check-activation', {
                    method: 'GET',
                });
                console.log(response);
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                const data = await response.json();
                console.log(data)
                setIsActivated(data.deviceActivation);
                console.log("Activation check result:", data.message);
            } catch (error) {
                console.error('Error checking activation status:', error);
                setIsActivated(false);
            }
        };

        checkActivation();
    }, []);

    if (isActivated === null) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 text-gray-700 dark:text-gray-300">
                <div className="flex items-center text-xl font-medium animate-pulse">
                    <Info className="mr-3 text-blue-500" size={24} />
                    Checking activation status...
                </div>
            </div>
        );
    }

    return (
        <ThemeProvider >
            <div className="min-h-screen bg-gradient-to-br from-gray-100 via-gray-50 to-blue-50 dark:from-[#111827] dark:via-black dark:to-[#10151b] text-gray-900 dark:text-white transition-colors duration-500">
                <Header />
                {isActivated ? (
                    <Dashboard />
                ) : (
                    // // <SystemActivation onActivationSuccess={() => setIsActivated(true)} />
                    // <div>
                    //     {/* Navigation Tabs */}
                    //     <div className="bg-white/50 backdrop-blur-sm dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-700">
                    //         <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    //             <nav className="flex space-x-8">
                    //                 {tabs.map((tab) => {
                    //                     const IconComponent = tab.icon;
                    //                     return (
                    //                         <button
                    //                             key={tab.id}
                    //                             onClick={() => setActiveTab(tab.id)}
                    //                             className={`py-4 px-1 border-b-2 font-medium text-sm flex items-center space-x-2 transition-colors duration-200 ${
                    //                                 activeTab === tab.id
                    //                                     ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                    //                                     : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300 hover:border-gray-300'
                    //                             }`}
                    //                         >
                    //                             <IconComponent size={18} />
                    //                             <span>{tab.name}</span>
                    //                         </button>
                    //                     );
                    //                 })}
                    //             </nav>
                    //         </div>
                    //     </div>
                        
                    //     {/* Tab Content */}
                    //     {renderContent()}
                    // </div>
                    <SystemActivation onActivationSuccess={() => setIsActivated(true)} />
                )}
            </div>
        </ThemeProvider>
    );
}