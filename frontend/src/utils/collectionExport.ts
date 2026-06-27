import { requestBlob } from '@/api/http';
import type { Collection } from '@/types/collection';
import type { CollectionItem } from '@/types/collectionItem';

export type CollectionExportFormat = 'pdf' | 'excel';

export type CollectionExportOptions = {
    format: CollectionExportFormat;
    pdfColumns: 2 | 3;
    includeBasePrice: boolean;
    includeSalePrice: boolean;
};

const PDF_PAGE_MARGIN = 12;
const PDF_CARD_GAP = 6;
const PDF_HEADER_HEIGHT = 22;

type CachedImageAsset = {
    dataUrl: string;
    format: 'PNG' | 'JPEG';
    width: number;
    height: number;
};

const imageCache = new Map<string, CachedImageAsset | null>();

function sanitizeFileName(value: string): string {
    return value
        .normalize('NFKD')
        .replace(/[^\w\s-]/g, '')
        .trim()
        .replace(/\s+/g, '-')
        .toLowerCase();
}

function buildFileName(collectionName: string, extension: string): string {
    const safeCollectionName = sanitizeFileName(collectionName || 'coleccion');
    const stamp = new Date().toISOString().slice(0, 10);
    return `${safeCollectionName}-${stamp}.${extension}`;
}

function formatMoney(value: number | string | null | undefined, currency = 'USD'): string {
    return new Intl.NumberFormat('es-CL', {
        style: 'currency',
        currency,
        maximumFractionDigits: 2
    }).format(Number(value ?? 0));
}

function resolveEdition(item: CollectionItem): string {
    return item.card.set_name || 'Edicion desconocida';
}

function resolveCondition(item: CollectionItem): string {
    return item.condition || 'Sin estado';
}

function resolveLanguage(item: CollectionItem): string {
    return item.language || 'Sin idioma';
}

function resolveFinish(item: CollectionItem): string {
    const finish = item.finish || 'Normal';
    return item.is_pokeball ? `${finish} Pokeball` : finish;
}

async function blobToDataUrl(blob: Blob): Promise<string> {
    return await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => resolve(String(reader.result || ''));
        reader.onerror = () => reject(reader.error);
        reader.readAsDataURL(blob);
    });
}

async function measureImage(dataUrl: string): Promise<{ width: number; height: number }> {
    return await new Promise((resolve, reject) => {
        const image = new Image();
        image.onload = () => {
            resolve({
                width: image.naturalWidth || image.width,
                height: image.naturalHeight || image.height
            });
        };
        image.onerror = () => reject(new Error('No fue posible medir la imagen.'));
        image.src = dataUrl;
    });
}

function detectImageFormat(dataUrl: string): 'PNG' | 'JPEG' {
    return dataUrl.startsWith('data:image/jpeg') || dataUrl.startsWith('data:image/jpg') ? 'JPEG' : 'PNG';
}

async function createImageAsset(blob: Blob): Promise<CachedImageAsset> {
    const dataUrl = await blobToDataUrl(blob);
    const { width, height } = await measureImage(dataUrl);

    return {
        dataUrl,
        format: detectImageFormat(dataUrl),
        width,
        height
    };
}

async function loadImageAsset(cardId: number, fallbackUrl: string | null | undefined): Promise<CachedImageAsset | null> {
    const cacheKey = `card:${cardId}:${fallbackUrl || 'none'}`;

    if (!cardId && !fallbackUrl) {
        return null;
    }

    if (imageCache.has(cacheKey)) {
        return imageCache.get(cacheKey) ?? null;
    }

    try {
        const blob = await requestBlob(`/cards/${cardId}/image?size=small`);
        const asset = await createImageAsset(blob);
        imageCache.set(cacheKey, asset);
        return asset;
    } catch {
        if (!fallbackUrl) {
            imageCache.set(cacheKey, null);
            return null;
        }

        try {
            const response = await fetch(fallbackUrl);
            if (!response.ok) {
                imageCache.set(cacheKey, null);
                return null;
            }

            const blob = await response.blob();
            const asset = await createImageAsset(blob);
            imageCache.set(cacheKey, asset);
            return asset;
        } catch {
            imageCache.set(cacheKey, null);
            return null;
        }
    }
}

function fitImage(width: number, height: number, maxWidth: number, maxHeight: number): { width: number; height: number } {
    if (width <= 0 || height <= 0) {
        return { width: maxWidth, height: maxHeight };
    }

    const scale = Math.min(maxWidth / width, maxHeight / height);
    return {
        width: width * scale,
        height: height * scale
    };
}

function buildExcelRows(items: CollectionItem[], options: CollectionExportOptions): Array<Record<string, string | number>> {
    return items.map((item) => {
        const row: Record<string, string | number> = {
            Nombre: item.card.name,
            Edicion: resolveEdition(item),
            Rareza: item.card.rarity || 'Sin rareza',
            Estado: resolveCondition(item),
            Acabado: resolveFinish(item),
            Cantidad: item.quantity
        };

        if (options.includeBasePrice) {
            row['Precio TCG'] = Number(item.base_price ?? 0);
            row['Moneda TCG'] = item.base_price_currency || 'USD';
        }

        if (options.includeSalePrice) {
            row['Precio venta'] = Number(item.sale_price ?? 0);
            row['Moneda venta'] = item.base_price_currency || 'USD';
        }

        return row;
    });
}

export async function exportCollectionToExcel(
    collection: Collection,
    items: CollectionItem[],
    options: CollectionExportOptions
): Promise<void> {
    const XLSX = await import('xlsx');
    const workbook = XLSX.utils.book_new();
    const worksheet = XLSX.utils.json_to_sheet(buildExcelRows(items, options));

    const columnWidths = Object.keys(buildExcelRows(items.slice(0, 1), options)[0] || {}).map((key) => ({
        wch: Math.max(key.length + 2, 16)
    }));
    worksheet['!cols'] = columnWidths;

    XLSX.utils.book_append_sheet(workbook, worksheet, 'Coleccion');
    XLSX.writeFile(workbook, buildFileName(collection.name, 'xlsx'));
}

function getPdfCardHeight(options: CollectionExportOptions): number {
    let height = options.pdfColumns === 2 ? 52 : 46;
    if (options.includeBasePrice) {
        height += 5;
    }
    if (options.includeSalePrice) {
        height += 5;
    }
    return height;
}

export async function exportCollectionToPdf(
    collection: Collection,
    items: CollectionItem[],
    options: CollectionExportOptions
): Promise<void> {
    const { jsPDF } = await import('jspdf');
    const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
    const pageWidth = doc.internal.pageSize.getWidth();
    const pageHeight = doc.internal.pageSize.getHeight();
    const columns = options.pdfColumns;
    const cardWidth = (pageWidth - PDF_PAGE_MARGIN * 2 - PDF_CARD_GAP * (columns - 1)) / columns;
    const cardHeight = getPdfCardHeight(options);

    doc.setFont('helvetica', 'bold');
    doc.setFontSize(18);
    doc.text(collection.name || 'Coleccion', PDF_PAGE_MARGIN, 14);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(9);
    doc.text(`Exportado el ${new Date().toLocaleString('es-CL')}`, PDF_PAGE_MARGIN, 20);

    let x = PDF_PAGE_MARGIN;
    let y = PDF_PAGE_MARGIN + PDF_HEADER_HEIGHT;

    for (let index = 0; index < items.length; index += 1) {
        const item = items[index];

        if (y + cardHeight > pageHeight - PDF_PAGE_MARGIN) {
            doc.addPage();
            x = PDF_PAGE_MARGIN;
            y = PDF_PAGE_MARGIN + 6;
        }

        doc.setDrawColor(217, 222, 229);
        doc.setFillColor(255, 255, 255);
        doc.roundedRect(x, y, cardWidth, cardHeight, 5, 5, 'FD');

        const imageAsset = await loadImageAsset(item.card.id, item.card.image_small);
        const innerX = x + 4;
        const innerY = y + 4;
        const innerHeight = cardHeight - 8;
        const imageBoxWidth = Math.min(cardWidth * 0.34, options.pdfColumns === 2 ? 28 : 21);
        const imageBoxHeight = innerHeight;
        const textGap = 4;
        const textX = innerX + imageBoxWidth + textGap;
        const textWidth = cardWidth - (textX - x) - 4;
        let contentY = innerY + 4;

        if (imageAsset) {
            try {
                const fitted = fitImage(imageAsset.width, imageAsset.height, imageBoxWidth, imageBoxHeight);
                const imageX = innerX + (imageBoxWidth - fitted.width) / 2;
                const imageY = innerY + (imageBoxHeight - fitted.height) / 2;
                doc.addImage(imageAsset.dataUrl, imageAsset.format, imageX, imageY, fitted.width, fitted.height, undefined, 'FAST');
            } catch {
                doc.setDrawColor(222, 226, 231);
                doc.roundedRect(innerX, innerY + 2, imageBoxWidth, imageBoxHeight - 4, 3, 3, 'S');
                doc.setFontSize(8);
                doc.text('Imagen no', innerX + 2, innerY + imageBoxHeight / 2 - 1);
                doc.text('disponible', innerX + 2, innerY + imageBoxHeight / 2 + 3);
            }
        } else {
            doc.setDrawColor(222, 226, 231);
            doc.roundedRect(innerX, innerY + 2, imageBoxWidth, imageBoxHeight - 4, 3, 3, 'S');
            doc.setFontSize(8);
            doc.text('Imagen no', innerX + 2, innerY + imageBoxHeight / 2 - 1);
            doc.text('disponible', innerX + 2, innerY + imageBoxHeight / 2 + 3);
        }

        doc.setFont('helvetica', 'bold');
        doc.setTextColor(20, 20, 20);
        doc.setFontSize(options.pdfColumns === 2 ? 11 : 10);
        const nameLines = doc.splitTextToSize(item.card.name, textWidth);
        doc.text(nameLines.slice(0, 2), textX, contentY);
        contentY += Math.min(nameLines.length, 2) * 4.4 + 1.5;

        doc.setFont('helvetica', 'normal');
        doc.setFontSize(options.pdfColumns === 2 ? 8.8 : 8.2);
        const lines = [
            `Rareza: ${item.card.rarity || 'Sin rareza'}`,
            `Estado: ${resolveCondition(item)}`,
            `Edicion: ${resolveEdition(item)}`,
            `Acabado: ${resolveFinish(item)}`,
            `Idioma: ${resolveLanguage(item)}`,
            `Cantidad: ${item.quantity}`
        ];

        if (options.includeBasePrice) {
            lines.push(`Precio TCG: ${formatMoney(item.base_price, item.base_price_currency || 'USD')}`);
        }

        if (options.includeSalePrice) {
            lines.push(`Precio venta: ${formatMoney(item.sale_price, item.base_price_currency || 'USD')}`);
        }

        for (const line of lines) {
            const wrapped = doc.splitTextToSize(line, textWidth);
            doc.text(wrapped.slice(0, 2), textX, contentY);
            contentY += wrapped.length > 1 ? 6.6 : 4.6;
        }

        const isLastColumn = (index + 1) % columns === 0;
        if (isLastColumn) {
            x = PDF_PAGE_MARGIN;
            y += cardHeight + PDF_CARD_GAP;
        } else {
            x += cardWidth + PDF_CARD_GAP;
        }
    }

    doc.save(buildFileName(collection.name, 'pdf'));
}
