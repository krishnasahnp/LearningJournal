document.addEventListener('DOMContentLoaded', () => {
    loadReflections();
    setupFormSubmission();
});

function setupFormSubmission() {
    const form = document.getElementById('journalForm');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        console.log('Form submitted! Processing...');

        // Basic client-side validation
        if (!form.checkValidity()) {
            // Let browser handle default validation UI or add custom here
            return;
        }

        const formData = new FormData(form);
        const tech = [];
        form.querySelectorAll('input[name="tech"]:checked').forEach(cb => tech.push(cb.value));

        const entry = {
            week: formData.get('week'),
            title: formData.get('journalName'),
            date: formData.get('date'),
            taskName: formData.get('taskName'),
            reflection: formData.get('taskDescription'),
            location: {
                lat: formData.get('geoLat'),
                lon: formData.get('geoLon'),
                address: formData.get('geoAddress')
            },
            tech: tech
        };

        try {
            const response = await fetch('/api/entries', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(entry)
            });

            if (response.ok) {
                alert('Journal entry saved successfully!');
                form.reset();
                loadReflections(); // Reload the list
            } else {
                const errorData = await response.json();
                alert(`Error saving entry: ${errorData.message}`);
            }
        } catch (error) {
            console.error('Error submitting form:', error);
            alert('Error submitting form. Make sure the server is running.');
        }
    });
}

async function loadReflections() {
    const journalList = document.getElementById('userJournalList');
    const counterDisplay = document.getElementById('reflectionCounter'); // We'll add this to HTML

    if (!journalList) return;

    try {
        const response = await fetch(`backend/reflections.json?t=${Date.now()}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const reflections = await response.json();

        // Update Counter
        if (counterDisplay) {
            counterDisplay.textContent = `${reflections.length} Entries`;
        }

        // Clear existing entries in the dynamic section (if any)
        journalList.innerHTML = '';

        // Sort reflections by date (newest first) - optional but good UX
        reflections.sort((a, b) => new Date(b.date) - new Date(a.date));

        reflections.forEach(entry => {
            const card = document.createElement('div');
            card.className = 'journal-card fade-in visible'; // Add visible class immediately for now

            // Format date nicely
            const dateOptions = { year: 'numeric', month: 'long', day: 'numeric' };
            const formattedDate = new Date(entry.date).toLocaleDateString('en-US', dateOptions);

            // Create tags HTML
            const tagsHtml = entry.tech && Array.isArray(entry.tech)
                ? entry.tech.map(t => `<span class="tag">${t}</span>`).join('')
                : '';

            // Create location HTML
            let locationHtml = '';
            if (entry.location) {
                if (entry.location.address) {
                    locationHtml = `<p style="color:var(--gray); font-size: 0.9em; margin-top: 0.5rem;">📍 ${entry.location.address}</p>`;
                } else if (entry.location.lat && entry.location.lon) {
                    locationHtml = `<p style="color:var(--gray); font-size: 0.9em; margin-top: 0.5rem;">📍 ${entry.location.lat}, ${entry.location.lon}</p>`;
                }
            }

            card.innerHTML = `
                <div class="journal-header">
                    <span class="week-badge">Week ${entry.week}</span>
                    <h3>${entry.title}</h3>
                    <p class="journal-date">${formattedDate}</p>
                </div>
                <div class="journal-body">
                    <div class="journal-question">
                        <h4>Task: ${entry.taskName || 'Journal Entry'}</h4>
                        <p>${entry.reflection}</p>
                    </div>
                    ${locationHtml}
                    <div class="journal-tags">
                        ${tagsHtml}
                    </div>
                </div>
            `;
            journalList.appendChild(card);
        });

    } catch (error) {
        console.error('Error loading reflections:', error);
        journalList.innerHTML = '<p style="text-align:center; color: var(--gray);">No local reflections found or error loading data.</p>';
    }
}
