(function () {
  const form = document.querySelector('#filter-form');
  if (!form) {
    return;
  }

  const endpoint = form.dataset.endpoint;
  if (!endpoint) {
    return;
  }

  const resultsContainer = document.querySelector('[data-role="results-container"]');
  const resultsTitle = document.querySelector('[data-role="results-title"]');
  const resultsCount = document.querySelector('[data-role="results-count"]');
  const ingredientField = form.querySelector('[data-role="ingredient-field"]');
  const chipsContainer = form.querySelector('[data-role="ingredient-chips"]');
  const clearButton = form.querySelector('[data-role="clear-filters"]');
  const queryInput = form.querySelector('input[name="q"]');
  const pageInput = form.querySelector('input[name="page"]');
  const autoSubmitInputs = form.querySelectorAll('[data-auto-submit="change"]');

  let debounceTimer = null;
  let latestRequestId = 0;
  let pendingQuerySync = null;

  function buildParams(page) {
    const params = new URLSearchParams();
    const formData = new FormData(form);
    formData.set('page', String(page));

    formData.forEach((value, key) => {
      if (typeof value !== 'string') {
        return;
      }
      const trimmed = value.trim();
      if (key === 'page') {
        params.set(key, String(page));
        return;
      }
      if (trimmed === '') {
        return;
      }
      params.append(key, trimmed);
    });

    return params;
  }

  function updateHistory(params, page) {
    const historyParams = new URLSearchParams(params);
    if (page <= 1) {
      historyParams.delete('page');
    }
    const queryString = historyParams.toString();
    const newUrl = queryString ? `${window.location.pathname}?${queryString}` : window.location.pathname;
    window.history.replaceState(null, '', newUrl);
  }

  function setLoading(isLoading) {
    if (!resultsContainer) {
      return;
    }
    if (isLoading) {
      resultsContainer.dataset.loading = 'true';
    } else {
      delete resultsContainer.dataset.loading;
    }
  }

  function fetchResults(page) {
    if (!resultsContainer) {
      return;
    }
    const params = buildParams(page);
    const requestId = ++latestRequestId;
    setLoading(true);

    fetch(`${endpoint}?${params.toString()}`, {
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
      },
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Request failed with status ${response.status}`);
        }
        return response.json();
      })
      .then((payload) => {
        if (requestId !== latestRequestId) {
          return;
        }
        if (typeof payload !== 'object' || payload === null) {
          return;
        }
        if (payload.html) {
          resultsContainer.innerHTML = payload.html;
        }
        if (payload.meta) {
          const { heading, subtitle, page: currentPage } = payload.meta;
          if (resultsTitle && heading) {
            resultsTitle.textContent = heading;
          }
          if (resultsCount && subtitle) {
            resultsCount.textContent = subtitle;
          }
          if (pageInput && currentPage) {
            pageInput.value = String(currentPage);
          }
          updateHistory(params, Number(currentPage || page));
        }
        if (payload.filters) {
          if (queryInput) {
            const serverQuery = payload.filters.query || '';
            if (document.activeElement === queryInput) {
              pendingQuerySync = serverQuery;
            } else {
              queryInput.value = serverQuery;
              pendingQuerySync = null;
            }
          }
          syncIngredientChips(payload.filters.ingredients || []);
          syncCheckboxGroup('cuisine', payload.filters.cuisines || []);
          syncCheckboxGroup('meal', payload.filters.meals || []);
          syncCheckboxGroup('diet', payload.filters.diets || []);
        }
      })
      .catch((error) => {
        if (requestId === latestRequestId) {
          console.error('Failed to refresh recipes', error);
        }
      })
      .finally(() => {
        if (requestId === latestRequestId) {
          setLoading(false);
        }
      });
  }

  function scheduleFetch(page) {
    if (debounceTimer) {
      window.clearTimeout(debounceTimer);
    }
    debounceTimer = window.setTimeout(() => fetchResults(page), 250);
  }

  function createChipElement(value) {
    const chip = document.createElement('li');
    chip.className = 'chip';
    chip.dataset.value = value;

    const label = document.createElement('span');
    label.textContent = value;
    chip.appendChild(label);

    const removeButton = document.createElement('button');
    removeButton.type = 'button';
    removeButton.className = 'chip-remove';
    removeButton.setAttribute('aria-label', `Remove ingredient ${value}`);
    removeButton.textContent = '×';
    chip.appendChild(removeButton);

    const hiddenInput = document.createElement('input');
    hiddenInput.type = 'hidden';
    hiddenInput.name = 'ingredient';
    hiddenInput.value = value;
    chip.appendChild(hiddenInput);

    return chip;
  }

  function addIngredient(rawValue) {
    if (!chipsContainer) {
      return false;
    }
    const normalized = rawValue.trim().toLowerCase();
    if (!normalized) {
      return false;
    }
    if (chipsContainer.querySelector(`[data-value="${CSS.escape(normalized)}"]`)) {
      return false;
    }
    const chip = createChipElement(normalized);
    chipsContainer.appendChild(chip);
    return true;
  }

  function removeIngredientChip(button) {
    const chip = button.closest('.chip');
    if (chip) {
      chip.remove();
    }
  }

  function syncIngredientChips(values) {
    if (!chipsContainer) {
      return;
    }
    const desired = new Set((values || []).map((value) => String(value).toLowerCase()));
    chipsContainer.querySelectorAll('.chip').forEach((chip) => {
      const value = chip.dataset.value || '';
      if (!desired.has(value.toLowerCase())) {
        chip.remove();
      }
    });
    desired.forEach((value) => {
      if (!chipsContainer.querySelector(`[data-value="${CSS.escape(value)}"]`)) {
        const chip = createChipElement(value);
        chipsContainer.appendChild(chip);
      }
    });
  }

  function syncCheckboxGroup(name, values) {
    if (!form) {
      return;
    }
    const desired = new Set((values || []).map((value) => String(value)));
    const selector = `input[name="${name}"]`;
    form.querySelectorAll(selector).forEach((element) => {
      if (element instanceof HTMLInputElement) {
        element.checked = desired.has(element.value);
      }
    });
  }

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    if (pageInput) {
      pageInput.value = '1';
    }
    fetchResults(1);
  });

  if (queryInput) {
    queryInput.addEventListener('input', () => {
      if (pageInput) {
        pageInput.value = '1';
      }
      scheduleFetch(1);
    });
    queryInput.addEventListener('blur', () => {
      if (pendingQuerySync !== null) {
        queryInput.value = pendingQuerySync;
        pendingQuerySync = null;
      }
    });
  }

  if (ingredientField) {
    ingredientField.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') {
        event.preventDefault();
        const added = addIngredient(ingredientField.value || '');
        if (added) {
          ingredientField.value = '';
          if (pageInput) {
            pageInput.value = '1';
          }
          fetchResults(1);
        }
      }
    });
  }

  if (chipsContainer) {
    chipsContainer.addEventListener('click', (event) => {
      const button = event.target.closest('.chip-remove');
      if (!button) {
        return;
      }
      event.preventDefault();
      removeIngredientChip(button);
      if (pageInput) {
        pageInput.value = '1';
      }
      fetchResults(1);
    });
  }

  autoSubmitInputs.forEach((input) => {
    input.addEventListener('change', () => {
      if (pageInput) {
        pageInput.value = '1';
      }
      fetchResults(1);
    });
  });

  if (clearButton) {
    clearButton.addEventListener('click', () => {
      if (queryInput) {
        queryInput.value = '';
        pendingQuerySync = null;
      }
      if (chipsContainer) {
        chipsContainer.innerHTML = '';
      }
      if (ingredientField) {
        ingredientField.value = '';
      }
      autoSubmitInputs.forEach((input) => {
        if (input instanceof HTMLInputElement && input.type === 'checkbox') {
          input.checked = false;
        }
      });
      if (pageInput) {
        pageInput.value = '1';
      }
      fetchResults(1);
    });
  }

  if (resultsContainer) {
    resultsContainer.addEventListener('click', (event) => {
      const link = event.target.closest('[data-page]');
      if (!link) {
        return;
      }
      const page = Number(link.getAttribute('data-page')) || 1;
      event.preventDefault();
      if (pageInput) {
        pageInput.value = String(page);
      }
      fetchResults(page);
    });
  }
})();
