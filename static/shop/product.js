document.addEventListener('DOMContentLoaded', () => {
    const reviewForm = document.querySelector('#review-form');
    const stars = document.querySelectorAll('#star-rating .fa-star');
    const ratingInput = document.querySelector('#rating-input');
    const productId = document.querySelector('#product-container').dataset.productId;

    // Star rating interaction
    if (stars && ratingInput) {
        stars.forEach(star => {
            star.addEventListener('click', () => {
                const value = star.dataset.value;
                ratingInput.value = value;
                stars.forEach(s => {
                    s.classList.toggle('text-warning', s.dataset.value <= value);
                    s.classList.toggle('text-muted', s.dataset.value > value);
                });
            });
        });
    }

    // Submit review (rating + optional comment)
    if (reviewForm) {
        reviewForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const rating = ratingInput.value;
            const content = reviewForm.querySelector('textarea[name="content"]').value.trim();

            if (!rating || rating < 1 || rating > 5) {
                alert('Please select a rating.');
                return;
            }

            try {
                const formData = new URLSearchParams();
                formData.append('rating', rating);
                if (content) formData.append('content', content);

                const response = await fetch(`/shop/product/${productId}/review`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: formData.toString()
                });
                const result = await response.json();

                if (result.success) {
                    // Update average rating
                    document.querySelector('.star-rating').innerHTML = `
                        ${[...Array(5)].map((_, i) => `
                            <i class="fas fa-star ${i < Math.round(result.avg_rating) ? 'text-warning' : 'text-muted'}"></i>
                        `).join('')}
                    `;

                    // Add new comment if provided
                    if (result.comment) {
                        const commentSection = document.createElement('div');
                        commentSection.className = 'card mb-3';
                        commentSection.innerHTML = `
                            <div class="card-body">
                                <div class="d-flex justify-content-between">
                                    <div>
                                        <strong>${result.comment.user_name}</strong>
                                        <div class="star-rating">
                                            ${[...Array(5)].map((_, i) => `
                                                <i class="fas fa-star ${i < rating ? 'text-warning' : 'text-muted'}"></i>
                                            `).join('')}
                                        </div>
                                    </div>
                                    <small class="text-muted">${result.comment.created_at}</small>
                                </div>
                                <p class="mt-2">${result.comment.content}</p>
                            </div>
                        `;
                        const commentsSection = document.querySelector('#comments-section');
                        const noComments = commentsSection.querySelector('.text-muted');
                        if (noComments) noComments.remove();
                        commentsSection.insertBefore(commentSection, commentsSection.firstChild);
                    }

                    // Hide form after submission
                    document.querySelector('#review-form-container').innerHTML = `
                        <div class="alert alert-info">You have already reviewed this product.</div>
                    `;
                    alert('Review submitted!');
                } else {
                    alert('Error: ' + result.error);
                }
            } catch (error) {
                alert('Error submitting review: ' + error.message);
            }
        });
    }
});