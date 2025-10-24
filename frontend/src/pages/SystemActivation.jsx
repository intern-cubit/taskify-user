import React, { useState, useEffect } from 'react';
import { Computer, Fingerprint, Key, CheckCircle, XCircle, Info, Copy } from 'lucide-react';
import toast from 'react-hot-toast';

const SystemActivation = ({ onActivationSuccess }) => {
    const [systemId, setSystemId] = useState('Loading...');
    const [activationKey, setActivationKey] = useState('');
    const [message, setMessage] = useState('');
    const [isActivated, setIsActivated] = useState(false);
    const [isLoadingSystemInfo, setIsLoadingSystemInfo] = useState(true);
    const [isActivating, setIsActivating] = useState(false); // New state for activation loading
    const [requiresActivationKey, setRequiresActivationKey] = useState(false);
    const [isLoadingActivationStatus, setIsLoadingActivationStatus] = useState(true);
    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    const ACTIVATION_URL = "https://api-keygen.obzentechnolabs.com/api/sadmin/activate" //|| "http://localhost:5000/api/sadmin/activate"; //

    useEffect(() => {
        const fetchAllInfo = async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/system-info`, {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                });
                const data = await response.json();
                setSystemId(data.systemId);
            } catch (error) {
                console.error('Error fetching system info:', error);
                setSystemId('Error fetching');
                toast.error('Failed to fetch system information. Ensure the backend is running.');
            } finally {
                setIsLoadingSystemInfo(false);
            }

            try {
                const response = await fetch(`${API_BASE_URL}/check-activation`);
                const data = await response.json();
                if (response.ok && data.success && data.deviceActivation) {
                    setIsActivated(true);
                    setMessage('System is already activated!');
                    setRequiresActivationKey(false);
                    toast.success('System is already activated!');
                    if (onActivationSuccess) {
                        onActivationSuccess();
                    }
                } else {
                    setIsActivated(false);
                    setRequiresActivationKey(data.requiresActivationKey || true);

                    if (data.activationStatus === 'not_activated') {
                        setMessage('Please enter your activation key to activate this system.');
                    } else if (data.activationStatus === 'invalid') {
                        setMessage('Stored activation is no longer valid. Please enter your activation key.');
                    } else {
                        setMessage(data.message || 'System is not activated. Please enter your activation key.');
                    }
                }
            } catch (error) {
                console.error('Error checking initial activation status:', error);
                setMessage('Failed to check activation status. Please ensure the backend is running.');
                setRequiresActivationKey(true);
                setIsActivated(false);
                toast.error('Failed to check initial activation status.');
            } finally {
                setIsLoadingActivationStatus(false);
            }
        };

        fetchAllInfo();
    }, [API_BASE_URL, onActivationSuccess]);

    const handleActivate = async () => {
        if (!activationKey) {
            return;
        }

        if (isLoadingSystemInfo || isLoadingActivationStatus) {
            setMessage('System information or activation status is still loading. Please wait.');
            toast.warn('System information or activation status is still loading. Please wait.');
            return;
        }

        setIsActivating(true);
        try {
            const response = await fetch(`${API_BASE_URL}/activate-device`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    systemId,
                    activationKey,
                    appName: import.meta.env.VITE_APP_NAME || "taskify"  // Configurable app name

                }),
            });

            const data = await response.json();

            if (response.ok && data.success) {
                setMessage(data.message || 'Device activated successfully!');
                setIsActivated(data.success);
                setRequiresActivationKey(false);
                toast.success(data.message || 'Device activated successfully!');

                if (onActivationSuccess) {
                    onActivationSuccess();
                }
            } else {
                // Handle different activation failure types
                setIsActivated(false);

                const errorMessage = data.message || 'Activation failed. Please check your activation key.';
                setMessage(errorMessage);
                toast.error(errorMessage);

                console.error('Activation failed:', data);
            }
            setActivationKey('');

        } catch (error) {
            console.error('Network error during activation:', error);
            setMessage('Failed to activate. Please check your network connection and ensure the backend is running.');
            setIsActivated(false);
            toast.error('Failed to activate. Check network/backend connection.');
        } finally {
            setIsActivating(false); // Reset activating state
        }
    };

    const overallLoading = isLoadingSystemInfo || isLoadingActivationStatus;

    return (
        <div className="min-h-screen font-inter">
            <div className="p-4 sm:p-6 flex items-center justify-center min-h-[calc(100vh-80px)]">
                <div className="w-full max-w-2xl bg-white/70 backdrop-blur-lg border border-gray-200 dark:bg-[rgba(30,30,30,0.5)] dark:backdrop-blur-md dark:border-gray-800 rounded-2xl p-6 sm:p-8 shadow-xl">
                    <h1 className="text-3xl sm:text-4xl font-extrabold text-gray-900 dark:text-white mb-8 text-center leading-tight">
                        <Computer className="inline-block mr-3 text-blue-600 dark:text-blue-400" size={36} />
                        {import.meta.env.VITE_APP_DISPLAY_NAME || "System"} Activation Required
                    </h1>

                    <div className="bg-blue-50/70 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl p-5 mb-6 shadow-sm">
                        <h2 className="text-xl font-semibold text-blue-800 dark:text-blue-100 mb-4 flex items-center">
                            <Info className="mr-2" size={20} />
                            Your System Details
                        </h2>
                        <div className="space-y-3">
                            <div className="flex items-center text-gray-800 dark:text-gray-200">
                                <Fingerprint className="mr-3 text-blue-600 dark:text-blue-400" size={20} />
                                <span className="font-medium">System ID:</span>
                                <span className="ml-3 text-gray-600 dark:text-gray-300 break-all">{isLoadingSystemInfo ? 'Loading...' : systemId}</span>
                                {!isLoadingSystemInfo && (
                                    <button
                                        onClick={() => {
                                            navigator.clipboard.writeText(systemId);
                                            toast.success('System ID copied to clipboard!');
                                        }}
                                        className="ml-2 text-blue-500 dark:text-blue-300 hover:text-blue-700 dark:hover:text-blue-100 transition-all duration-150"
                                        title="Copy System ID"
                                    >
                                        <Copy size={16} />
                                    </button>
                                )}
                            </div>
                        </div>
                        {overallLoading && (
                            <div className="mt-4 text-center text-blue-600 dark:text-blue-400 animate-pulse">
                                Fetching system details and activation status...
                            </div>
                        )}
                    </div>

                    <div className="bg-white/70 backdrop-blur-sm border border-gray-200 dark:bg-[rgba(30,30,30,0.5)] dark:backdrop-blur-md dark:border-gray-800 rounded-xl p-6 shadow-sm mb-6">
                        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
                            <Key className="mr-2 text-blue-600 dark:text-blue-400" size={20} />
                            Enter Activation Key
                        </h2>
                        <div className="flex flex-col sm:flex-row gap-4">
                            <input
                                type="text"
                                placeholder="Enter your activation key here"
                                value={activationKey}
                                onChange={(e) => setActivationKey(e.target.value)}
                                className="flex-grow p-3 border border-gray-300 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-gray-50/70 dark:bg-[rgba(30,30,30,0.5)] dark:backdrop-blur-sm text-gray-900 dark:text-white shadow-inner text-base transition-all duration-200"
                                disabled={overallLoading || isActivated}
                            />
                            <button
                                onClick={handleActivate}
                                className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-lg shadow-md transition-all duration-300 ease-in-out transform hover:scale-105 flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed min-w-[140px]"
                                disabled={overallLoading || isActivated || isActivating}
                            >
                                {isActivating ? (
                                    <>
                                        <svg className="animate-spin -ml-1 mr-2 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                        </svg>
                                        Activating...
                                    </>
                                ) : isActivated ? (
                                    <>
                                        <CheckCircle className="mr-2" size={20} />
                                        Activated
                                    </>
                                ) : (
                                    <>
                                        <Key className="mr-2" size={20} />
                                        Activate
                                    </>
                                )}
                            </button>
                        </div>
                    </div>

                    <div className="bg-amber-50/70 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-5 mb-6 shadow-sm">
                        <h2 className="text-xl font-semibold text-amber-800 dark:text-amber-100 mb-4 flex items-center">
                            <Info className="mr-2" size={20} />
                            Need an Activation Key?
                        </h2>
                        <div className="space-y-3">
                            <p className="text-amber-700 dark:text-amber-200 text-sm leading-relaxed">
                                Contact us to get your activation key:
                            </p>
                            <div className="flex flex-col sm:flex-row gap-4">
                                <div className="flex items-center text-amber-800 dark:text-amber-200">
                                    <span className="font-medium">Phone:</span>
                                    <span className="ml-2">807494xxxx</span>
                                </div>
                                <div className="flex items-center text-amber-800 dark:text-amber-200">
                                    <span className="font-medium">Email:</span>
                                    <span className="ml-2">mail.market2market@gmail.com</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {message && (
                        <div className={`p-4 rounded-xl flex items-start ${isActivated ? 'bg-green-50/70 dark:bg-green-900/20 border border-green-200 dark:border-green-800 text-green-800 dark:text-green-200' : 'bg-red-50/70 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-800 dark:text-red-200'}`}>
                            {isActivated ? <CheckCircle className="mr-3 flex-shrink-0" size={20} /> : <XCircle className="mr-3 flex-shrink-0" size={20} />}
                            <p className="text-sm font-medium leading-relaxed">{message}</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default SystemActivation;