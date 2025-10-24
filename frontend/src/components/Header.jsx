import React, { useState, useEffect, useRef } from 'react';
import { Moon, Sun, LogOut, CheckCircle, XCircle, RefreshCcw, Power } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';

const Header = () => {
    const { isDark, toggleTheme } = useTheme();
    const [activationStatus, setActivationStatus] = useState(null);
    const [loadingStatus, setLoadingStatus] = useState(false);
    const [systemId, setSystemId] = useState(null);
    const [showStatusPopup, setShowStatusPopup] = useState(false);
    const statusButtonRef = useRef(null);
    const popupRef = useRef(null); // Ref for the popup itself

    useEffect(() => {
        const handleClickOutside = (event) => {
            // Check if the click is outside the button and the popup
            if (
                statusButtonRef.current && !statusButtonRef.current.contains(event.target) &&
                popupRef.current && !popupRef.current.contains(event.target)
            ) {
                setShowStatusPopup(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, []);

    const checkActivationStatus = async () => {
        setLoadingStatus(true);
        setActivationStatus(null);
        setSystemId(null);
        try {
            const response = await fetch('http://localhost:8000/check-activation');
            const data = await response.json();

            if (response.ok) {
                console.log('Activation status:', data.activationStatus);
                console.log('System ID:', data.systemId);
                setActivationStatus(data.activationStatus);
                setSystemId(data.systemId);
            } else {
                console.error('Failed to fetch activation status:', data.message || response.statusText);
                setActivationStatus('error');
                setSystemId('N/A');
            }
        } catch (error) {
            console.error('Error checking activation status:', error);
            setActivationStatus('error');
            setSystemId('N/A');
        } finally {
            setLoadingStatus(false);
        }
    };

    const handleLogout = async () => {
        try {
            const response = await fetch('http://localhost:8000/logout', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            if (response.ok) {
                if (window.electronAPI && window.electronAPI.showLogoutDialog) {
                    window.electronAPI.showLogoutDialog();
                } else {
                    alert('You have been logged out. The application will now restart.');
                    window.location.reload();
                }
            } else {
                console.error('Logout failed:', response.statusText);
                alert('Logout failed. Please try again.');
            }
        } catch (error) {
            console.error('Error during logout:', error);
            alert('An error occurred during logout.');
        }
    };

    // Initial fetch on component mount
    useEffect(() => {
        checkActivationStatus();
    }, []);

    const handleReloadApp = () => {
        if (window.electronAPI && window.electronAPI.reloadApp) {
            window.electronAPI.reloadApp();
        } else {
            console.warn("Electron API for reloading not available. Using window.location.reload().");
            window.location.reload();
        }
    };

    const handleQuitApp = () => {
        if (window.electronAPI && window.electronAPI.quitApp) {
            window.electronAPI.quitApp();
        } else {
            if (window.confirm("Are you sure you want to quit the application?")) {
                console.warn("Electron API for quitting not available. Using browser confirm.");
            }
        }
    };

    // Modified to just toggle the popup visibility
    const toggleStatusPopup = () => {
        setShowStatusPopup(!showStatusPopup);
        // No need to call checkActivationStatus here, as it's already done on mount.
        // The "Refresh" button inside the popup will handle re-fetching if needed.
    };

    return (
        <header className="flex justify-between items-center py-4 px-6 bg-white/70 backdrop-blur-sm border border-gray-200 dark:bg-[rgba(30,30,30,0.5)] dark:backdrop-blur-md dark:border dark:border-gray-800 shadow-sm">
            <div className="flex items-center">
                <h1 className="text-3xl font-extrabold text-blue-700">
                    Taskify
                </h1>
                {/* <span className="text-3xl font-extrabold text-gray-900 dark:text-white flex items-center">
                    Autofill
                </span> */}
                <p className="hidden md:block ml-4 text-gray-600 dark:text-gray-400 text-sm">
                    Making Tasks Simpler
                </p>
            </div>

            <div className="flex items-center space-x-4 relative">
                <button
                    ref={statusButtonRef}
                    onClick={toggleStatusPopup} // This now just toggles visibility
                    onMouseEnter={() => setShowStatusPopup(true)} // Show on hover
                    onMouseLeave={() => setShowStatusPopup(false)} // Hide on mouse leave (can be refined for better UX)
                    className="flex items-center p-2 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors duration-300 shadow-md"
                    aria-label="Check activation status"
                    disabled={loadingStatus}
                >
                    {loadingStatus ? (
                        <span className="animate-spin mr-2">⚙️</span>
                    ) : activationStatus === 'active' ? (
                        <CheckCircle className="text-green-500 mr-1" size={20} />
                    ) : activationStatus === 'inactive' ? (
                        <XCircle className="text-red-500 mr-1" size={20} />
                    ) : (
                        <span className="mr-1">Status</span>
                    )}
                    {loadingStatus ? 'Checking...' :
                        activationStatus === 'active' ? 'Active' :
                            activationStatus === 'inactive' ? 'Inactive' :
                                activationStatus === 'error' ? 'Error' : 'Check Status'}
                </button>

                {showStatusPopup && (
                    <div
                        ref={popupRef} // Assign ref to the popup
                        onMouseEnter={() => setShowStatusPopup(true)} // Keep visible when hovering over popup
                        onMouseLeave={() => setShowStatusPopup(false)} // Hide when mouse leaves popup
                        className={`absolute top-full right-0 mt-2 p-4 rounded-lg shadow-xl z-10
                                ${isDark ? 'bg-gray-800 text-gray-100 border border-gray-700' : 'bg-white text-gray-900 border border-gray-300'}`}
                        style={{ minWidth: '200px' }}
                    >
                        <h3 className="font-bold text-lg mb-2">Activation Details</h3>
                        <p className="text-sm">
                            <strong>Status: </strong>
                            <span className={activationStatus === 'active' ? 'text-green-500' : 'text-red-500'}>
                                {activationStatus ? activationStatus.toUpperCase() : 'UNKNOWN'}
                            </span>
                        </p>
                        <p className="text-sm">
                            <strong>System ID: </strong>
                            <span className="font-mono break-all">{systemId || 'Loading...'}</span>
                        </p>
                        {loadingStatus && (
                            <p className="text-sm flex items-center mt-2">
                                <span className="animate-spin mr-2">⚙️</span> Updating...
                            </p>
                        )}
                        {activationStatus === 'error' && (
                            <p className="text-sm text-red-400 mt-2">
                                <XCircle className="inline-block mr-1" size={16} /> Error fetching status.
                            </p>
                        )}
                        <button
                            onClick={checkActivationStatus} // This button will explicitly re-fetch the status
                            className="mt-3 w-full flex items-center justify-center px-3 py-1.5 text-sm rounded-md bg-blue-500 text-white hover:bg-blue-600 transition-colors duration-200"
                            disabled={loadingStatus}
                        >
                            <RefreshCcw className="mr-1" size={16} /> Refresh
                        </button>
                    </div>
                )}

                <button
                    onClick={handleReloadApp}
                    className="flex items-center p-2 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors duration-300 shadow-md"
                    aria-label="Reload Application"
                >
                    <RefreshCcw className="text-blue-500 mr-1" size={20} />
                    Reload
                </button>

                <button
                    onClick={handleQuitApp}
                    className="flex items-center p-2 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors duration-300 shadow-md"
                    aria-label="Quit Application"
                >
                    <Power className="text-purple-600 mr-1" size={20} />
                    Quit
                </button>

                <button
                    onClick={handleLogout}
                    className="flex items-center p-2 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors duration-300 shadow-md"
                    aria-label="Logout"
                >
                    <LogOut className="text-red-600 mr-1" size={20} />
                    Logout
                </button>

                <button
                    onClick={toggleTheme}
                    className="p-2 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors duration-300 shadow-md"
                    aria-label="Toggle theme"
                >
                    {isDark ? <Sun className="text-yellow-400" size={20} /> : <Moon className="text-blue-800" size={20} />}
                </button>
            </div>
        </header>
    );
};

export default Header;