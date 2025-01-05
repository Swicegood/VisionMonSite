export function getLatestImageUrl(cameraIndex) {
    return `/get_latest_image/${cameraIndex}/?t=${new Date().getTime()}`;
}

export function getCompositeImageUrl(cameraName) {
    return `/get_composite_image/${cameraName}/?t=${new Date().getTime()}`;
}

export function colorCodeState(element, state) {
    element.classList.remove('bg-primary', 'bg-secondary', 'bg-success', 'bg-danger', 'bg-warning', 'bg-info', 'text-white');

    const lowerState = state.toLowerCase();

    if (lowerState.includes('bustling')) {
        element.classList.add('bg-danger', 'text-white');
    } else if (lowerState.includes('night-time')) {
        element.classList.add('bg-secondary', 'text-white');
    } else if (lowerState.includes('big religious festival') || lowerState.includes('religious or spiritual gathering') 
        || lowerState.includes('eating') ) {
        element.classList.add('bg-warning');
    } else if (lowerState.includes('nothing')) {
        element.classList.add('bg-success', 'text-white');
    } else if (lowerState.includes('single person')) {
        element.classList.add('bg-info', 'text-white');
    } else {
        element.classList.add('bg-light');
    }
}

export function typeWriter(element, text, speed) {
    let i = 0;
    function type() {
        if (i < text.length) {
            element.innerHTML += text.charAt(i);
            i++;
            setTimeout(type, speed);
        }
    }
    type();
}

export function refreshImages() {
    const allImages = document.querySelectorAll('#camera-feeds img, #camera-states img');
    allImages.forEach(img => {
        const currentSrc = new URL(img.src);
        currentSrc.searchParams.set('t', new Date().getTime());
        img.src = currentSrc.toString();
    });
}